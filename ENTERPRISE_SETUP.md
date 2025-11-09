# Enterprise Setup Guide

회사 환경에서 사용하기 위한 상세 설정 가이드입니다.

## 📋 목차
- [전체 아키텍처](#전체-아키텍처)
- [멀티 Git 저장소 설정](#멀티-git-저장소-설정)
- [멀티 BigQuery 프로젝트 설정](#멀티-bigquery-프로젝트-설정)
- [LLM 선택 (GPT vs Gemini)](#llm-선택)
- [Confluence 계층 구조 설정](#confluence-계층-구조-설정)
- [실제 사용 예시](#실제-사용-예시)

## 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI                             │
│              (사용자 질문 입력 및 결과 표시)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│            Enhanced Data Analysis Agent (LangGraph)             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. Multi-Repo Analysis                                   │  │
│  │     • repo1, repo2, repo3, ...                           │  │
│  │     • 모든 저장소에서 SQL 패턴 학습                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  2. Schema Discovery                                      │  │
│  │     • project1, project2, project3, project4             │  │
│  │     • 모든 테이블 스키마 자동 탐색                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  3. Query Generation (GPT or Gemini)                     │  │
│  │     • 코드 패턴 + 스키마 → SQL 생성                        │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  4. Query Execution                                       │  │
│  │     • 적절한 프로젝트 자동 선택                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  5-7. Analysis & Documentation & Confluence               │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 멀티 Git 저장소 설정

### 설정 방법

`.env` 파일에 JSON 형식으로 여러 저장소 지정:

```bash
# 여러 Git 저장소 (JSON 배열)
GIT_REPOSITORIES=["https://github.com/company/analytics-queries.git", "https://github.com/company/data-warehouse.git", "https://github.com/company/bi-reports.git"]

# 모든 저장소에 적용되는 인증 토큰
GIT_TOKEN=ghp_your_personal_access_token

# 최대 분석 저장소 수 제한
MAX_REPOS_TO_ANALYZE=10

# 저장소당 최대 파일 수
MAX_FILES_PER_REPO=50
```

### 사용 시나리오

**시나리오: 회사의 모든 데이터 팀 저장소 분석**

```bash
GIT_REPOSITORIES=[
  "https://github.com/company/data-analytics.git",
  "https://github.com/company/bi-dashboard.git",
  "https://github.com/company/ml-pipeline.git",
  "https://github.com/company/data-quality.git",
  "https://github.com/company/reporting-queries.git"
]
```

에이전트는 모든 저장소에서:
- SQL 쿼리 패턴 추출
- 자주 사용되는 테이블 발견
- 일반적인 JOIN 패턴 학습
- CTE, Window Function 사용 패턴 파악

## 멀티 BigQuery 프로젝트 설정

### 설정 방법

```bash
# 4개의 BigQuery 프로젝트
BIGQUERY_PROJECTS=["company-prod", "company-analytics", "company-ml", "company-dwh"]

# 프로젝트별 주요 데이터셋 (선택사항)
BIGQUERY_DATASETS={
  "company-prod": ["sales", "customers", "products"],
  "company-analytics": ["reports", "dashboards"],
  "company-ml": ["features", "models"],
  "company-dwh": ["staging", "core", "marts"]
}

# 스키마 자동 탐색 활성화
AUTO_DISCOVER_SCHEMAS=true
```

### 작동 방식

1. **자동 스키마 탐색**
   - 초기화 시 모든 프로젝트의 데이터셋과 테이블 스캔
   - 각 테이블의 스키마 정보 캐싱
   - 쿼리 생성 시 LLM에게 전체 스키마 제공

2. **자동 프로젝트 선택**
   - 쿼리에 명시된 테이블명으로 프로젝트 자동 감지
   - 감지 실패 시 첫 번째 프로젝트 사용

3. **스키마 정보 활용**
   ```
   LLM이 받는 컨텍스트:

   === AVAILABLE BIGQUERY SCHEMAS ===

   📊 Project: company-prod
   ============================================================

     Dataset: sales (15 tables)
       • company-prod.sales.orders (1,234,567 rows)
         Fields:
           - order_id (STRING)
           - customer_id (STRING)
           - order_date (DATE)
           - amount (FLOAT64)
           ... and 12 more fields
       • company-prod.sales.customers (456,789 rows)
       ...
   ```

## LLM 선택

### GPT (OpenAI) 사용

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o  # 또는 gpt-4-turbo, gpt-3.5-turbo
```

### Gemini (Google) 사용

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-1.5-pro  # 또는 gemini-1.5-flash
```

### 선택 기준

| 기능 | GPT-4o | Gemini 1.5 Pro |
|------|--------|----------------|
| SQL 생성 정확도 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 복잡한 쿼리 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| BigQuery 문법 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 속도 | 빠름 | 매우 빠름 |
| 비용 | 중간 | 저렴 |
| 컨텍스트 길이 | 128K | 2M tokens |

**권장사항:**
- **GPT-4o**: 복잡한 비즈니스 로직이 필요한 경우
- **Gemini 1.5 Pro**: 대용량 스키마 분석, 비용 절감

## Confluence 계층 구조 설정

### 기본 설정

```bash
CONFLUENCE_URL=https://your-company.atlassian.net
CONFLUENCE_EMAIL=your-email@company.com
CONFLUENCE_API_TOKEN=your_api_token
CONFLUENCE_SPACE_KEY=DATA  # 데이터 팀 스페이스

# 부모 페이지 ID 지정 (특정 페이지 하위에 생성)
CONFLUENCE_PARENT_PAGE_ID=123456789
```

### 부모 페이지 ID 찾기

1. Confluence에서 목적 페이지로 이동
2. 페이지 우측 상단 "..." → "Page Information" 클릭
3. URL에서 `pageId=` 다음의 숫자가 Page ID
   ```
   https://company.atlassian.net/wiki/pages/viewinfo.action?pageId=123456789
                                                                    ^^^^^^^^^^^^
   ```

### 계층 구조 예시

```
📂 Data Team Space
  └── 📄 Data Analysis Reports (Page ID: 123456789) ← 이것을 PARENT_PAGE_ID로 설정
       └── 📄 [자동 생성] Data Analysis: 매출 분석 - 2024-01-15
       └── 📄 [자동 생성] Data Analysis: 고객 분석 - 2024-01-16
       └── 📄 [자동 생성] Data Analysis: 재고 현황 - 2024-01-17
```

## 실제 사용 예시

### 완전한 `.env` 파일 예시 (회사용)

```bash
# ============================================
# LLM Configuration
# ============================================
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o

GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-1.5-pro

# ============================================
# BigQuery Configuration (4개 프로젝트)
# ============================================
BIGQUERY_PROJECTS=["mycompany-prod", "mycompany-analytics", "mycompany-ml", "mycompany-staging"]

BIGQUERY_DATASETS={
  "mycompany-prod": ["sales", "inventory", "customers"],
  "mycompany-analytics": ["reports", "metrics", "kpis"],
  "mycompany-ml": ["features", "predictions"],
  "mycompany-staging": ["raw", "staging"]
}

# ============================================
# Confluence Configuration
# ============================================
CONFLUENCE_URL=https://mycompany.atlassian.net
CONFLUENCE_EMAIL=data-team@mycompany.com
CONFLUENCE_API_TOKEN=ATATT3xFfGF0...
CONFLUENCE_SPACE_KEY=DATA
CONFLUENCE_PARENT_PAGE_ID=987654321

# ============================================
# Git Repository Configuration
# ============================================
GIT_REPOSITORIES=[
  "https://github.com/mycompany/data-warehouse-queries.git",
  "https://github.com/mycompany/analytics-sql.git",
  "https://github.com/mycompany/bi-reports.git",
  "https://github.com/mycompany/ml-pipeline.git"
]

GIT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx

# ============================================
# Advanced Settings
# ============================================
MAX_REPOS_TO_ANALYZE=5
MAX_FILES_PER_REPO=100
AUTO_DISCOVER_SCHEMAS=true
```

### 사용 흐름

1. **에이전트 초기화**
   ```bash
   streamlit run app.py
   ```

   초기화 중 표시:
   ```
   🤖 Using LLM: openai - gpt-4o
   📂 Configured 4 Git repositories
   📦 Analyzing repository: https://github.com/mycompany/data-warehouse-queries.git
   ✓ Found 234 queries in 45 files
   📦 Analyzing repository: https://github.com/mycompany/analytics-sql.git
   ✓ Found 156 queries in 32 files
   ...
   📊 Configured 4 BigQuery projects
   🔍 Discovering BigQuery schemas across all projects...
     📊 Discovering schemas in project: mycompany-prod
       ✓ Found 8 datasets
     📊 Discovering schemas in project: mycompany-analytics
       ✓ Found 3 datasets
   ...
   📝 Confluence configured for space: DATA
   ```

2. **질문 입력**
   ```
   "지난 3개월간 매출 상위 10개 제품의 월별 추세를 보여줘"
   ```

3. **에이전트 실행**
   - 4개 저장소의 390개 쿼리 패턴 분석
   - 4개 프로젝트의 전체 스키마 참조
   - GPT-4o로 최적화된 BigQuery SQL 생성
   - 자동으로 올바른 프로젝트에서 실행
   - 결과 분석 및 인사이트 생성
   - Confluence 지정 위치에 문서 발행

## 권장 프로세스

### 1단계: 준비
- [ ] GitHub Personal Access Token 생성 (`repo` 권한)
- [ ] BigQuery 프로젝트 목록 확인
- [ ] Confluence API Token 생성
- [ ] Confluence 부모 페이지 ID 확인

### 2단계: 설정
- [ ] `.env.example`을 `.env`로 복사
- [ ] 모든 저장소 URL 나열
- [ ] 모든 BigQuery 프로젝트 ID 나열
- [ ] Confluence 정보 입력

### 3단계: 테스트
- [ ] 에이전트 초기화 (스키마 탐색 확인)
- [ ] 간단한 질문으로 테스트
- [ ] Confluence 문서 생성 확인

### 4단계: 운영
- [ ] 팀원들에게 사용법 교육
- [ ] 질문 템플릿 공유
- [ ] Confluence 문서 구조 정리

## 문제 해결

### 스키마 탐색이 너무 오래 걸림

```bash
# 스키마 자동 탐색 비활성화
AUTO_DISCOVER_SCHEMAS=false
```

대신 쿼리에 전체 테이블 경로 명시:
```sql
SELECT * FROM `mycompany-prod.sales.orders`
```

### 여러 저장소 분석이 느림

```bash
# 저장소 수 제한
MAX_REPOS_TO_ANALYZE=3

# 파일 수 제한
MAX_FILES_PER_REPO=30
```

### Confluence 특정 위치에 생성 안됨

- `CONFLUENCE_PARENT_PAGE_ID` 확인
- 해당 페이지에 대한 쓰기 권한 확인
- API 토큰 권한 확인

## 추가 리소스

- [GitHub Personal Access Token 생성](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [BigQuery 권한 설정](https://cloud.google.com/bigquery/docs/access-control)
- [Confluence API Token](https://id.atlassian.com/manage-profile/security/api-tokens)
