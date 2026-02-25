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
	AvailabilityZone string `json:"availability_zone"`
	DDDRequestTime   int64  `json:"ddd_request_time"`
}

type InvokeResult struct {
	InstanceType     string
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

	// Skip header
	_, err = reader.Read()
	if err != nil {
		return nil, fmt.Errorf("failed to read CSV header: %w", err)
	}

	var payloads []WorkerPayload
	for {
		record, err := reader.Read()
		if err != nil {
			break
		}

		if len(record) >= 2 {
			payloads = append(payloads, WorkerPayload{
				InstanceType:     record[0],
				AvailabilityZone: record[1],
			})
		}
	}

	return payloads, nil
}

func invokeWorker(ctx context.Context, payload WorkerPayload, wg *sync.WaitGroup, results chan<- InvokeResult) {
	defer wg.Done()

	result := InvokeResult{
		InstanceType:     payload.InstanceType,
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
		InvocationType: types.InvocationTypeEvent, // Async invocation - returns 202
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

	// Invoke all workers in parallel
	for _, payload := range payloads {
		payload.DDDRequestTime = dddRequestTime
		wg.Add(1)
		go invokeWorker(ctx, payload, &wg, results)
	}

	// Wait for all 202 responses
	wg.Wait()
	close(results)

	// Collect results
	successCount := 0
	failCount := 0
	var errors []string

	for result := range results {
		if result.Success {
			successCount++
		} else {
			failCount++
			errors = append(errors, fmt.Sprintf("%s/%s: %s", result.InstanceType, result.AvailabilityZone, result.Error))
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
