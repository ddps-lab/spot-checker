#!/usr/bin/env python3
"""
현재 디렉토리의 tester.sh, tester.go, azure.csv 파일을 읽어서
이 3개 파일을 생성하는 setup_files.sh를 자동으로 만듭니다.

사용법: python generate_setup_files.py
"""

import os
import sys


def read_file(filename):
    """파일을 읽어서 내용을 반환합니다."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ 오류: {filename} 파일을 찾을 수 없습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 오류: {filename} 읽기 실패: {e}")
        sys.exit(1)


def generate_setup_script(tester_sh_content, tester_go_content, azure_csv_content):
    """setup_files.sh 스크립트를 생성합니다."""
    
    # tester.sh의 실행 권한 체크
    tester_sh_has_shebang = tester_sh_content.startswith('#!/bin/bash')
    
    script = """#!/bin/bash
# 이 스크립트는 tester.sh, tester.go, azure.csv 파일들을 자동으로 생성합니다.
# 이 파일은 generate_setup_files.py로 자동 생성되었습니다.

echo "파일 생성 시작..."

# tester.sh 생성
cat > tester.sh << 'EOF'
"""
    
    script += tester_sh_content
    
    script += """
EOF

chmod +x tester.sh
echo "✓ tester.sh 생성 완료"

# tester.go 생성
cat > tester.go << 'EOF'
"""
    
    script += tester_go_content
    
    script += """
EOF

echo "✓ tester.go 생성 완료"

# azure.csv 생성
cat > azure.csv << 'EOF'
"""
    
    script += azure_csv_content
    
    script += """
EOF

echo "✓ azure.csv 생성 완료"

echo ""
echo "==================================="
echo "모든 파일 생성이 완료되었습니다!"
echo "==================================="
echo "생성된 파일 목록:"
echo "  - tester.sh"
echo "  - tester.go"
echo "  - azure.csv"
echo ""
echo "사용법:"
echo "  1. EC2에 업로드: scp setup_files.sh ec2-user@<EC2-IP>:~/"
echo "  2. EC2에서 실행: ./setup_files.sh"
echo "  3. 환경변수 설정: export function_url=<Lambda-Function-URL>"
echo "  4. 테스트 실행: ./tester.sh"
echo ""
"""
    
    return script


def main():
    print("=" * 60)
    print("setup_files.sh 생성 스크립트")
    print("=" * 60)
    print()
    
    # 1. 3개 파일 읽기
    print("📖 파일 읽기 중...")
    
    tester_sh = read_file('tester.sh')
    print("  ✓ tester.sh 읽기 완료")
    
    tester_go = read_file('tester.go')
    print("  ✓ tester.go 읽기 완료")
    
    azure_csv = read_file('azure.csv')
    print("  ✓ azure.csv 읽기 완료")
    
    print()
    
    # 2. setup_files.sh 생성
    print("🔨 setup_files.sh 생성 중...")
    
    setup_script = generate_setup_script(tester_sh, tester_go, azure_csv)
    
    # 3. 파일로 저장
    output_file = 'setup_files.sh'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(setup_script)
        
        # 실행 권한 부여
        os.chmod(output_file, 0o755)
        
        print(f"  ✓ {output_file} 생성 완료")
        print()
        
        # 4. 파일 크기 정보
        tester_sh_lines = len(tester_sh.splitlines())
        tester_go_lines = len(tester_go.splitlines())
        azure_csv_lines = len(azure_csv.splitlines())
        setup_lines = len(setup_script.splitlines())
        
        print("=" * 60)
        print("📊 생성 완료!")
        print("=" * 60)
        print(f"입력 파일:")
        print(f"  - tester.sh: {tester_sh_lines} 줄")
        print(f"  - tester.go: {tester_go_lines} 줄")
        print(f"  - azure.csv: {azure_csv_lines} 줄 (헤더 포함)")
        print()
        print(f"출력 파일:")
        print(f"  - {output_file}: {setup_lines} 줄")
        print()
        print("✅ 성공적으로 생성되었습니다!")
        print()
        print("다음 단계:")
        print(f"  1. ./{output_file} 실행하여 테스트")
        print(f"  2. EC2로 전송: scp {output_file} ec2-user@<EC2-IP>:~/")
        print()
        
    except Exception as e:
        print(f"❌ 오류: {output_file} 저장 실패: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

