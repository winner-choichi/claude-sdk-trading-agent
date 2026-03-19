# Claude SDK 트레이딩 에이전트

Claude Agent SDK, Alpaca, Slack를 기반으로 만든 자율형 트레이딩 에이전트 저장소입니다. 우선은 안전한 페이퍼 트레이딩 운영을 목표로 하고, 그 위에 승인 훅, 리포팅, 백테스트, 자기 조정형 전략 진화 흐름을 쌓아가는 구조입니다.

## 이 저장소에 들어있는 것

- `trading_agent/`: 실제 파이썬 애플리케이션, 설정 템플릿, 설치 가이드, 구현 문서
- `PLAN.md`: 아키텍처, 운영 흐름, 단계별 로드맵을 Mermaid로 시각화한 계획 문서

## 주요 특징

- 승인 훅과 리스크 제한을 포함한 자율 트레이딩 흐름
- 주문과 시세 조회를 위한 Alpaca 연동
- 알림, 명령어, 승인 처리를 위한 Slack 봇 지원
- 백테스트 및 전략 최적화 지원
- SQLite 기반 영속성 계층
- `Dockerfile`을 포함한 배포 지향 구조

## 저장소 구조

```text
.
├── PLAN.md
├── README.md
└── trading_agent/
    ├── agent/
    ├── config/
    ├── docs/
    ├── hooks/
    ├── messaging/
    ├── storage/
    ├── tests/
    ├── tools/
    ├── Dockerfile
    ├── README.md
    ├── main.py
    ├── requirements.txt
    └── verify_setup.py
```

## 빠른 시작

1. Python 3.11+ 가상환경을 만듭니다.
2. [`trading_agent/requirements.txt`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/requirements.txt)로 의존성을 설치합니다.
3. [`trading_agent/config/config.example.yaml`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/config/config.example.yaml)을 `trading_agent/config/config.yaml`로 복사합니다.
4. Alpaca 키와 필요한 경우 Slack 자격 정보를 입력합니다.
5. `trading_agent/` 디렉터리에서 페이퍼 트레이딩 모드로 실행합니다.

```bash
cd trading_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
python main.py
```

## 설정 메모

- 기본 모드는 `PAPER_TRADING`이며, 처음에는 이 모드로 시작하는 것이 안전합니다.
- Slack은 선택 사항이지만 승인 흐름과 운영 모니터링은 Slack 설정이 있을 때 가장 잘 동작합니다.
- `config.yaml`, 로그, SQLite 데이터, 스크린샷 같은 로컬 실행 산출물은 의도적으로 git 추적에서 제외했습니다.

## 문서 안내

- 제품 및 실행 계획: [`PLAN.md`](/Users/choechiwon/toys/claudeAgentSDK/PLAN.md)
- 앱 상세 안내: [`trading_agent/README.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/README.md)
- 빠른 시작 가이드: [`trading_agent/docs/setup/QUICKSTART.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/docs/setup/QUICKSTART.md)
- Slack 설정 가이드: [`trading_agent/docs/setup/slack_bot_setup.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/docs/setup/slack_bot_setup.md)
- 승인 흐름 문서: [`trading_agent/docs/APPROVAL_FLOW.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/docs/APPROVAL_FLOW.md)
- 구현 상태 문서: [`trading_agent/docs/development/IMPLEMENTATION_STATUS.md`](/Users/choechiwon/toys/claudeAgentSDK/trading_agent/docs/development/IMPLEMENTATION_STATUS.md)

## 현재 상태

이 저장소에는 이미 애플리케이션 골격, 트레이딩 도구, Slack 메시징 계층, 저장소 계층, 설치 문서, 테스트가 포함되어 있습니다. 다음 단계는 설정을 더 단단하게 다듬고, 실제 환경에서 엔드투엔드 검증을 거친 뒤, 계획서에 정리한 자율 전략 및 백테스트 루프를 반복 개선하는 것입니다.
