# T3 다변화에 따른 DDD fulfill 횟수 수집 코드

---

### 사용 방법:

1. 실험 대상으로 할 Region들에 대해 `create_log_group.py` 와 `create_tester.py`를 완료한다.
2. 각 실험 대상 Region에 켜진 멀티노드 DDD 수집용 EC2에 Session Manager로 접속한다.
3. EC2 인스턴스의 홈 디렉토리에 `vim m.py`로 vim 창을 띄운 후, `middleware_t3_test_data_set_eachregion.py`의 내용을 붙여넣는다.
그리고 붙여놓은 파일에서 전역변수 `REGION`을 해당 인스턴스의 Region으로 변경한다.
4. `[Esc]+ :wq + [엔터]`로 빠져나간다.
5. `vim tester_gen.sh`로 vim 창을 띄운 후, `middleware_t3_tester_gen_ec2.sh`의 내용을 붙여놓는다.
이후 마찬가지로 `[Esc]+ :wq + [엔터]`로 빠져나간다.
6. `bash tesetr_gen.sh` 를 실행한다.
7. `ls` 명령어를 통해 작업중인 홈 디렉토리에 `test_loop.sh`이 생성되었는지 확인한다.
8. `nohup bash test_loop.sh &` 명령어를 입력하여 실험을 시작한다

실험 대상 T3는 [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50] 이며, 별다른 수정없이 진행하는 경우 실험 한 번이 반복되는 주기는 70분으로 설정되어있다.
