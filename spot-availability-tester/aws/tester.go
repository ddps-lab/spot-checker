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
		AvailabilityZone string `json:"availability_zone"`
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
		data.Inputs.InstanceType = ""
		data.Inputs.DDDRequestTime = 0

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
	for {
		record, err := csvReader.Read()
		if err != nil {
			break
		}

		requestData := RequestData{}
		requestData.Inputs.DDDRequestTime = 0
		requestData.Inputs.InstanceType = record[0]
		requestData.Inputs.AvailabilityZone = record[1]

		requestDataList = append(requestDataList, requestData)
	}

	spawnRateNum, err := strconv.Atoi(spawnRate)
	ticker := time.NewTicker(time.Duration(spawnRateNum) * time.Minute)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			var wg sync.WaitGroup
			nowTime := int(time.Now().Unix())
			for _, data := range requestDataList {
				data.Inputs.DDDRequestTime = nowTime
				jsonData, err := json.Marshal(data)
				if err != nil {
					fmt.Printf("JSON Encoding Error: %v", err)
					continue
				}
				wg.Add(1)
				go predict(functionUrl, jsonData, &wg)
			}
			wg.Wait()
		}
	}
}
