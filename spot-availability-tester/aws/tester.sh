#!/bin/bash
filename="test_file.csv"
spawnrate="3"

lines=$(wc -l < "$filename")
tasks=$((lines - 1))

# warm bench request lambda instances
go run tester.go --task_num $tasks --function_url $function_url --file_name "unknown" --spawn_rate $spawnrate
sleep 5
go run tester.go --task_num $tasks --function_url $function_url --file_name "unknown" --spawn_rate $spawnrate
sleep 5
go run tester.go --task_num $tasks --function_url $function_url --file_name $filename --spawn_rate $spawnrate