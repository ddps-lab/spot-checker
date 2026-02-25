package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	lambdaClient "github.com/aws/aws-sdk-go-v2/service/lambda"
	"github.com/aws/aws-sdk-go-v2/service/lambda/types"
)

type WorkerPayload struct {
	InstanceType     string `json:"instance_type"`
	Region           string `json:"region"`
	AvailabilityZone string `json:"availability_zone"`
	DDDRequestTime   int64  `json:"ddd_request_time"`
	RowIndex         int    `json:"row_index"`
}

type InvokeResult struct {
	InstanceType     string
	Region           string
	AvailabilityZone string
	Success          bool
	Error            string
}

var (
	workerFunctionName string
	client             *lambdaClient.Client
)

func init() {
	workerFunctionName = os.Getenv("WORKER_FUNCTION_NAME")
	if workerFunctionName == "" {
		panic("WORKER_FUNCTION_NAME environment variable is required")
	}

	cfg, err := config.LoadDefaultConfig(context.Background())
	if err != nil {
		panic(fmt.Sprintf("unable to load SDK config: %v", err))
	}

	client = lambdaClient.NewFromConfig(cfg)
}

func loadCSV(filename string) ([]WorkerPayload, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to open CSV file: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)

	_, err = reader.Read()
	if err != nil {
		return nil, fmt.Errorf("failed to read CSV header: %w", err)
	}

	var payloads []WorkerPayload
	rowIndex := 0
	for {
		record, err := reader.Read()
		if err != nil {
			break
		}

		if len(record) >= 4 {
			payloads = append(payloads, WorkerPayload{
				InstanceType:     record[0] + "_" + record[1],
				Region:           record[2],
				AvailabilityZone: record[3],
				RowIndex:         rowIndex,
			})
			rowIndex++
		}
	}

	return payloads, nil
}

func invokeWorker(ctx context.Context, payload WorkerPayload, wg *sync.WaitGroup, results chan<- InvokeResult) {
	defer wg.Done()

	result := InvokeResult{
		InstanceType:     payload.InstanceType,
		Region:           payload.Region,
		AvailabilityZone: payload.AvailabilityZone,
		Success:          true,
	}

	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("failed to marshal payload: %v", err)
		results <- result
		return
	}

	_, err = client.Invoke(ctx, &lambdaClient.InvokeInput{
		FunctionName:   aws.String(workerFunctionName),
		InvocationType: types.InvocationTypeEvent,
		Payload:        jsonPayload,
	})

	if err != nil {
		result.Success = false
		result.Error = fmt.Sprintf("failed to invoke worker: %v", err)
	}

	results <- result
}

func handler(ctx context.Context) (map[string]interface{}, error) {
	payloads, err := loadCSV("data.csv")
	if err != nil {
		return nil, fmt.Errorf("failed to load CSV: %w", err)
	}

	dddRequestTime := time.Now().Unix()

	var wg sync.WaitGroup
	results := make(chan InvokeResult, len(payloads))

	for _, payload := range payloads {
		payload.DDDRequestTime = dddRequestTime
		wg.Add(1)
		go invokeWorker(ctx, payload, &wg, results)
	}

	wg.Wait()
	close(results)

	successCount := 0
	failCount := 0
	var errors []string

	for result := range results {
		if result.Success {
			successCount++
		} else {
			failCount++
			errors = append(errors, fmt.Sprintf("%s/%s/%s: %s", result.InstanceType, result.Region, result.AvailabilityZone, result.Error))
		}
	}

	return map[string]interface{}{
		"total":   len(payloads),
		"success": successCount,
		"failed":  failCount,
		"errors":  errors,
	}, nil
}

func main() {
	lambda.Start(handler)
}
