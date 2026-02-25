package main

import (
	"bytes"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"
)

type RequestData struct {
	Inputs struct {
		DDDRequestTime   int    `json:"ddd_request_time"`
		InstanceType     string `json:"instance_type"`
		Region           string `json:"region"`
		AvailabilityZone string `json:"availability_zone"`
		RowIndex         int    `json:"row_index"`
	} `json:"inputs"`
}

func predict(serverAddress string, jsonData []byte, wg *sync.WaitGroup) {
	resp, err := http.Post(serverAddress, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Printf("HTTP 요청 에러: %v", err)
		return
	}
	defer resp.Body.Close()
	wg.Done()
}

func main() {
	var functionUrl string
	var taskNum string
	var fileName string
	var spawnRate string
	args := os.Args
	for i := 1; i < len(args); i += 2 {
		option := args[i]
		value := args[i+1]

		switch option {
		case "--function_url":
			functionUrl = value
		case "--task_num":
			taskNum = value
		case "--file_name":
			fileName = value
		case "--spawn_rate":
			spawnRate = value
		default:
			fmt.Println("Error: unknown option")
			os.Exit(1)
		}
	}

	if fileName == "unknown" {
		var wg sync.WaitGroup
		num, err := strconv.Atoi(taskNum)
		if err != nil {
			fmt.Printf("Invalid task number: %v", err)
			return
		}
		data := RequestData{}
		data.Inputs.AvailabilityZone = ""
		data.Inputs.Region = ""
		data.Inputs.InstanceType = ""
		data.Inputs.DDDRequestTime = 0
		data.Inputs.RowIndex = 0

		jsonData, err := json.Marshal(data)
		if err != nil {
			fmt.Printf("JSON Encoding Error: %v", err)
			return
		}
		for i := 0; i < num; i++ {
			wg.Add(1)
			go predict(functionUrl, jsonData, &wg)
		}
		wg.Wait()
		return
	}

	file, err := os.Open(fileName)
	if err != nil {
		fmt.Println("Error opening file:", err)
		return
	}
	defer file.Close()

	csvReader := csv.NewReader(file)

	_, err = csvReader.Read()
	if err != nil {
		fmt.Println("Error reading header:", err)
		return
	}

	var requestDataList []RequestData
	rowIndex := 0
	for {
		record, err := csvReader.Read()
		if err != nil {
			break
		}

	// Azure CSV 형식: InstanceTier,InstanceType,Region,AZ
	// Column 0: InstanceTier (예: Standard)
	// Column 1: InstanceType (예: E64-16ds_v4)
	// Column 2: Region (예: CL Central)
	// Column 3: AZ (예: 1, 2, 3, Single)
	
	if len(record) < 4 {
		fmt.Printf("Invalid CSV row (expected at least 4 columns): %v\n", record)
		continue
	}

	requestData := RequestData{}
	requestData.Inputs.DDDRequestTime = 0
	// Azure VM 크기 형식: {Tier}_{InstanceType} (예: Standard_E64-16ds_v4)
	requestData.Inputs.InstanceType = record[0] + "_" + record[1]
	requestData.Inputs.Region = record[2]
	requestData.Inputs.AvailabilityZone = record[3]
	requestData.Inputs.RowIndex = rowIndex

		requestDataList = append(requestDataList, requestData)
		fmt.Printf("[DEBUG CSV] Row %d: Type=%s, Region=%s, AZ=%s\n", 
			rowIndex, requestData.Inputs.InstanceType, 
			requestData.Inputs.Region, requestData.Inputs.AvailabilityZone)
		rowIndex++
	}
	
	fmt.Printf("\n[INFO] Total %d requests loaded from CSV\n\n", len(requestDataList))

	spawnRateNum, err := strconv.Atoi(spawnRate)
	ticker := time.NewTicker(time.Duration(spawnRateNum) * time.Minute)
	defer ticker.Stop()

	requestCount := 0
	for {
		select {
		case <-ticker.C:
			requestCount++
			fmt.Printf("\n[BATCH %d] Sending %d requests at %s\n", 
				requestCount, len(requestDataList), time.Now().Format("15:04:05"))
			
			var wg sync.WaitGroup
			nowTime := int(time.Now().Unix())
			
			// 인덱스로 직접 접근하여 복사 문제 방지
			for idx := 0; idx < len(requestDataList); idx++ {
				// 복사본 생성
				data := requestDataList[idx]
				data.Inputs.DDDRequestTime = nowTime
				
				// 처음 3개만 상세 로그
				if idx < 3 {
					fmt.Printf("[DEBUG SEND] Request %d: RowIndex=%d, Type=%s, Region=%s\n", 
						idx, data.Inputs.RowIndex, data.Inputs.InstanceType, data.Inputs.Region)
				}
				
				jsonData, err := json.Marshal(data)
				if err != nil {
					fmt.Printf("JSON Encoding Error: %v", err)
					continue
				}
				
				// 첫 번째 요청의 JSON 출력
				if idx == 0 {
					fmt.Printf("[DEBUG JSON] First request: %s\n", string(jsonData))
				}
				
				wg.Add(1)
				go predict(functionUrl, jsonData, &wg)
			}
			wg.Wait()
			fmt.Printf("[BATCH %d] All requests completed\n", requestCount)
		}
	}
}
