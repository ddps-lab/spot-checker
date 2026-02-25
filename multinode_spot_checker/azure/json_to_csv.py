"""
JSON 로그를 CSV로 변환하는 스크립트
(export_result.py가 자동으로 CSV 변환하므로 이 스크립트는 백업용)
"""
import json
import csv
import os
import sys
from glob import glob


def json_to_csv(json_file):
    """JSON 파일을 CSV로 변환"""
    print(f"Converting {json_file}...")
    
    # JSON 파일 읽기
    records = []
    with open(json_file, 'r') as f:
        for line in f:
            try:
                record = json.loads(line.strip())
                records.append(record)
            except:
                pass
    
    if not records:
        print(f"  No valid JSON records found")
        return
    
    # CSV 파일명 생성
    csv_file = json_file.replace('.json', '.csv')
    
    # CSV로 저장
    if records:
        keys = records[0].keys()
        
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(records)
        
        print(f"  ✅ Saved to {csv_file} ({len(records)} records)")


def main():
    print("\n⚠️  Note: export_result.py now exports directly to CSV via S3.")
    print("This script is for manual JSON to CSV conversion only.\n")
    
    # result_data 디렉토리에서 JSON 파일 찾기
    if not os.path.exists('result_data'):
        print("❌ result_data directory not found")
        sys.exit(1)
    
    json_files = glob('result_data/**/*.json', recursive=True)
    
    if not json_files:
        print("❌ No JSON files found in result_data/")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"Converting JSON to CSV")
    print(f"{'='*70}")
    print(f"Found {len(json_files)} JSON files\n")
    
    for json_file in json_files:
        json_to_csv(json_file)
    
    print(f"\n{'='*70}")
    print(f"✅ Conversion completed!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()

