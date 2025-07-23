# ✈️ FirstAirline-core (2nd Team Project)
## 🌊 프로젝트 소개

**FirstAirline**는 Azure 환경에서  
외부 데이터를 수집, 정제, 분석, 시각화하는 **엔드-투-엔드 데이터 응용 프로그램**을 구현하는 프로젝트입니다.

이 프로젝트의 목표는, 팀원이 함께 실무에 가까운 데이터 파이프라인을 구축하며  
**Python, SQL, Power BI, Databricks, Azure Data Factory Azure Functions, Stream Analytics, Azure ML, Power BI**에 대한 실전 경험을 쌓는 것입니다.

> **"저희 `FIRST` 항공사를 찾아주셔서 감사합니다. 데이터 여행의 목적지로 안전히 모시겠습니다." – First AirLine**


## 🏗️ 아키텍처 개요

```plaintext
📦 외부 데이터 소스 (API / 웹 / CSV)
    ↓
🐍 데이터 수집 및 정제 (Python, Azure Data Factory, Databricks)
    ↓
💾 Azure PostgreSQL 저장소 (PostgreSQL)
    ↓
🧠 데이터 분석 (Azure ML, Databricks) 
    ↓
📊 Power BI 대시보드 연결 및 시각화 (Powe BI, Flask)
```

## 🛠️ 기술 스택

| 구분           | 사용 기술                                       |
|----------------|------------------------------------------------|
| 데이터 수집     | Python, Azure Functions, Event Hub, Stream Analytics, Postgresql  |
| 데이터 처리     | Python, Databricks, Azure Data Factory             |
| 저장 및 분산처리 | Databricks, Azure Data Factory, PostgreSQL                |
| 시각화         | Power BI, Flask                                       |
| 버전관리       | Git + GitHub                                   |

## 📁 디렉토리 구조
``` bash
FirstAirline-core/
└── README.md
```

## 👥 팀원 및 역할 분담

| 이름 | 역할            | 담당 업무                                  |
|------|-----------------|---------------------------------------------|
| 김진우   | Data Engineer  |  프로젝트 관리, 데이터 수집/정제, 시각화 구현               |
| 박상필   | Data Engineer   |   데이터 수집/정제, 웹 구현           |
| 박형진    | Data Engineer         |  데이터 수집/정제, 데이터 품질 관리             |
| 서상원    | Data Engineer    |   데이터 수집/정제, ML분석                 |
| 송누림    | Data Engineer         |  데이터 파이프라인 설계, 데이터 수집/정제, 시각화 구현          |
| 임승수    | Data Engineer         |   데이터 수집/정제, ML분석, 트러블 슈팅 관리               |


## 📈 결과 요약
- 실시간 혼잡도 예측
공항 터미널별·시간대별로 혼잡도 상태(여유/보통/혼잡 등) 예측 및 제공
- 항공편 지연 안내
항공편별로 예측된 지연 정보 및 시간 안내
- 맞춤형 정보 제공
사용자가 입력한 항공편, 터미널, 주차장 등 필요한 정보만 한 번에 보여주는 서비스
- 주차장 혼잡도 안내
주차장별 실시간/예측 혼잡도 및 추천 주차장 안내
- 대시보드 시각화
Power BI, Fabric 등 대시보드에서 데이터 실시간 시각화 및 공유
- 자동화 데이터 파이프라인
Azure Databricks/Data Factory 활용 자동 수집·정제·적재 파이프라인 구현
- 챗봇 서비스
외국인도 쉽게 이용할 수 있도록 다국어 챗봇 연동
- 운영/보안 강화
비용, 활동로그, 보안관리 자동화로 운영 안정성 확보

