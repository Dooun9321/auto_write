# Auto Write - Enterprise Data Analysis Agent

LangGraph 기반의 엔터프라이즈급 자동 데이터 분석 및 문서 작성 에이전트입니다. 여러 Git 저장소와 BigQuery 프로젝트를 동시에 분석하고, GPT 또는 Gemini를 선택하여 사용할 수 있습니다.

## 🌟 주요 기능

### 🔄 멀티 소스 통합
- **멀티 Git 저장소 분석**: 회사의 모든 데이터 저장소를 동시에 분석하여 SQL 패턴 학습
- **멀티 BigQuery 프로젝트**: 여러 프로젝트(최대 10개)의 데이터를 자동으로 탐색 및 쿼리
- **자동 스키마 탐색**: 모든 프로젝트의 테이블 스키마를 자동으로 발견하고 LLM에게 제공

### 🤖 유연한 LLM 선택
- **GPT-4o / GPT-4 Turbo**: OpenAI의 강력한 SQL 생성 능력
- **Gemini 1.5 Pro**: Google의 대용량 컨텍스트 처리 및 비용 효율성
- **실시간 전환**: 환경 설정만으로 LLM 제공자 변경 가능

### 📊 인텔리전트 분석
- **컨텍스트 기반 쿼리 생성**: 기존 쿼리 패턴 + 스키마 정보 → 최적화된 SQL
- **자동 프로젝트 선택**: 쿼리 내용 분석하여 적절한 BigQuery 프로젝트 자동 선택
- **오류 자동 수정**: 쿼리 실행 오류 시 자동으로 수정 및 재시도

### 📝 전문 문서화
- **AI 기반 인사이트**: 데이터 결과를 분석하여 비즈니스 인사이트 자동 생성
- **Confluence 계층 구조**: 지정된 페이지 하위에 체계적으로 문서 생성
- **멀티 프로젝트 추적**: 어떤 프로젝트의 어떤 데이터를 사용했는지 자동 기록

### 💼 엔터프라이즈 기능
- **Private 저장소 지원**: Personal Access Token 기반 인증
- **대규모 스키마 처리**: 수백 개의 테이블 스키마 자동 관리
- **병렬 분석**: 여러 저장소를 동시에 분석하여 빠른 초기화
- **캐싱 최적화**: 스키마 정보 캐싱으로 반복 작업 고속화

## 🚀 빠른 시작 (회사 환경)

**5분 안에 설정:**
```bash
# 1. 저장소 클론
git clone <your-repo-url>
cd auto_write

# 2. 환경 설정
cp .env.example .env
# .env 파일 편집 (아래 예시 참고)

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 실행
streamlit run app.py
```

**`.env` 파일 예시 (회사용):**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

BIGQUERY_PROJECTS=["company-prod", "company-analytics", "company-ml", "company-dwh"]

GIT_REPOSITORIES=["https://github.com/company/repo1.git", "https://github.com/company/repo2.git"]
GIT_TOKEN=ghp_...

CONFLUENCE_URL=https://company.atlassian.net
CONFLUENCE_API_TOKEN=...
CONFLUENCE_PARENT_PAGE_ID=123456789
```

**👉 [상세 설정 가이드 (ENTERPRISE_SETUP.md)](./ENTERPRISE_SETUP.md)**

## 🏗️ 엔터프라이즈 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│            Enhanced Data Analysis Agent (LangGraph)             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. Multi-Repo Analysis (repo1, repo2, ...)              │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  2. Schema Discovery (project1-4 × datasets × tables)    │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  3. Query Generation (GPT-4o or Gemini 1.5 Pro)         │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  4. Multi-Project Execution (auto project selection)    │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────┐   │
│  │  3. Query Execution         │   │  BigQuery 실행
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │  4. Result Analysis         │   │  결과 분석
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │  5. Documentation           │   │  문서 생성
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │  6. Confluence Publishing   │   │  문서 발행
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 📁 프로젝트 구조

```
auto_write/
├── app.py                      # Streamlit 애플리케이션
├── requirements.txt            # Python 의존성
├── .env.example               # 환경 변수 예제
├── README.md
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py           # LangGraph 워크플로우
│   │   └── state.py           # 에이전트 상태 정의
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── bigquery_tool.py   # BigQuery 연동
│   │   ├── code_analyzer.py   # Git 코드 분석
│   │   ├── query_generator.py # SQL 쿼리 생성
│   │   └── confluence_tool.py # Confluence 연동
│   └── utils/
│       ├── __init__.py
│       └── config.py          # 설정 관리
└── examples/
    └── sample_queries.sql     # 샘플 쿼리
```

## 🚀 시작하기

### 1. 필수 요구사항

- Python 3.9+
- Google Cloud 계정 (BigQuery 액세스)
- OpenAI API 키
- Confluence 계정 (선택사항)

### 2. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd auto_write

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 설정

`.env` 파일을 생성하고 필요한 설정을 입력합니다:

```bash
cp .env.example .env
```

`.env` 파일 내용:

```bash
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Google Cloud Project
GCP_PROJECT_ID=your_gcp_project_id
BIGQUERY_DATASET=your_dataset_name

# Confluence (선택사항)
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_EMAIL=your_email@example.com
CONFLUENCE_API_TOKEN=your_confluence_api_token
CONFLUENCE_SPACE_KEY=your_space_key

# Git Repository (로컬 경로 또는 원격 URL)
GIT_REPO_PATH=./
# 또는 원격 저장소: GIT_REPO_PATH=https://github.com/user/repo.git

# Git 인증 (private 원격 저장소인 경우 필요)
GIT_TOKEN=your_github_personal_access_token
```

#### Git 저장소 설정

**로컬 저장소 사용:**
```bash
GIT_REPO_PATH=./  # 현재 디렉토리
# 또는
GIT_REPO_PATH=/path/to/your/local/repo
```

**원격 저장소 사용 (Public):**
```bash
GIT_REPO_PATH=https://github.com/username/repository.git
```

**원격 저장소 사용 (Private - 인증 필요):**

1. **GitHub Personal Access Token 생성:**
   - GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - "Generate new token" 클릭
   - `repo` 권한 선택
   - 토큰 복사

2. **환경 변수 설정:**
```bash
GIT_REPO_PATH=https://github.com/username/private-repo.git
GIT_TOKEN=ghp_your_token_here
```

**GitLab/Bitbucket도 동일한 방식으로 지원됩니다:**
```bash
# GitLab
GIT_REPO_PATH=https://gitlab.com/username/repo.git
GIT_TOKEN=your_gitlab_token

# Bitbucket
GIT_REPO_PATH=https://bitbucket.org/username/repo.git
GIT_TOKEN=your_bitbucket_token
```

### 4. Google Cloud 인증

BigQuery 사용을 위한 인증 설정:

```bash
# Application Default Credentials 설정
gcloud auth application-default login

# 또는 서비스 계정 키 파일 사용
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### 5. 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`로 접속합니다.

## 📖 사용 방법

### 기본 사용법

1. **에이전트 초기화**: 사이드바에서 "Initialize Agent" 버튼 클릭
2. **질문 입력**: 데이터 분석 질문을 입력
3. **분석 실행**: "Analyze" 버튼 클릭
4. **결과 확인**: 생성된 쿼리, 결과, 분석, 문서 확인

### 예제 질문

```
- 지난달 매출 상위 10개 제품은 무엇인가요?
- 2024년 고객별 총 매출을 보여주세요
- 신규 사용자 가입의 월별 추세를 분석해주세요
- 반품률이 가장 높은 제품은 무엇인가요?
- 고객 세그먼트별 평균 주문 금액을 계산해주세요
```

## 🔧 설정 옵션

### BigQuery

`src/utils/config.py`에서 BigQuery 관련 설정을 수정할 수 있습니다:

- `GCP_PROJECT_ID`: Google Cloud 프로젝트 ID
- `BIGQUERY_DATASET`: 기본 데이터셋 이름

### LLM 모델

쿼리 생성과 분석에 사용되는 모델을 변경하려면:

```python
# src/tools/query_generator.py
self.llm = ChatOpenAI(
    api_key=api_key,
    model="gpt-4o",  # 또는 "gpt-4-turbo", "gpt-3.5-turbo"
    temperature=0.1
)
```

### Confluence

Confluence 통합을 사용하지 않으려면 `.env` 파일에서 Confluence 관련 설정을 비워두면 됩니다. 에이전트는 자동으로 Confluence 발행 단계를 건너뜁니다.

## 🛠️ 개발

### 새로운 도구 추가

`src/tools/` 디렉토리에 새로운 도구를 추가할 수 있습니다:

```python
# src/tools/my_tool.py
class MyTool:
    def __init__(self, config):
        self.config = config

    def execute(self, input_data):
        # 도구 로직
        return result
```

### 워크플로우 수정

`src/agent/graph.py`에서 LangGraph 워크플로우를 수정할 수 있습니다:

```python
def _build_graph(self) -> StateGraph:
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("new_step", self._new_step_node)

    # 엣지 정의
    workflow.add_edge("previous_step", "new_step")
    workflow.add_edge("new_step", "next_step")

    return workflow.compile()
```

## 🧪 테스트

```bash
# 개별 컴포넌트 테스트
python -c "from src.tools.code_analyzer import CodeAnalyzer; \
analyzer = CodeAnalyzer('./'); \
print(analyzer.analyze_repository())"

# BigQuery 연결 테스트
python -c "from src.tools.bigquery_tool import BigQueryTool; \
from src.utils.config import Config; \
bq = BigQueryTool(Config.GCP_PROJECT_ID); \
print(bq.execute_query('SELECT 1 as test'))"
```

## 📊 작동 원리

### 1. 코드 분석 (Code Analysis)

- Git 저장소에서 `.sql`, `.py` 등의 파일을 스캔
- 정규표현식으로 SQL 쿼리 추출
- 테이블 참조, 쿼리 패턴, 일반적인 구조 분석
- 학습된 패턴을 쿼리 생성에 활용

### 2. 쿼리 생성 (Query Generation)

- 사용자 질문과 코드 컨텍스트를 LLM에 전달
- BigQuery 문법에 맞는 SQL 쿼리 생성
- 설명과 가정사항 함께 제공
- 오류 발생 시 자동으로 쿼리 수정

### 3. 쿼리 실행 (Query Execution)

- BigQuery API를 통해 쿼리 실행
- 결과를 DataFrame으로 변환
- 기본 통계 정보 생성
- 실행 메타데이터 (처리된 바이트, 캐시 히트 등) 수집

### 4. 결과 분석 (Result Analysis)

- LLM을 사용하여 쿼리 결과 분석
- 주요 발견사항, 트렌드, 패턴 식별
- 인사이트와 권장사항 생성
- 제한사항 및 주의사항 명시

### 5. 문서 생성 (Documentation)

- 전체 분석 과정을 구조화된 문서로 작성
- 경영진 요약, 방법론, 주요 발견사항 포함
- Confluence XHTML 형식으로 포맷팅
- 기술적/비기술적 독자 모두를 고려

### 6. Confluence 발행 (Publishing)

- Confluence API를 통해 페이지 생성
- 메타데이터와 라벨 추가
- 페이지 URL 반환하여 접근 가능

## 🤝 기여

기여를 환영합니다! Pull Request를 제출해주세요.

## 📝 라이센스

MIT License

## 🙏 크레딧

- [LangGraph](https://github.com/langchain-ai/langgraph) - 에이전트 워크플로우
- [LangChain](https://github.com/langchain-ai/langchain) - LLM 통합
- [Streamlit](https://streamlit.io/) - UI 프레임워크
- [Google Cloud BigQuery](https://cloud.google.com/bigquery) - 데이터 웨어하우스
- [Atlassian Confluence](https://www.atlassian.com/software/confluence) - 문서 플랫폼

## ❓ 문제 해결

### BigQuery 인증 오류

```bash
# Application Default Credentials 재설정
gcloud auth application-default login
```

### Confluence 연결 오류

- Confluence URL이 올바른지 확인 (예: `https://your-domain.atlassian.net`)
- API 토큰이 유효한지 확인
- 공간 키(Space Key)가 정확한지 확인

### LLM 응답 오류

- OpenAI API 키가 유효한지 확인
- API 사용량 제한을 확인
- 모델 이름이 올바른지 확인

### Git 저장소 접근 오류

**"Failed to clone repository" 오류:**

1. **URL 확인:**
   - 저장소 URL이 올바른지 확인
   - `.git` 확장자가 포함되어 있는지 확인
   - 예: `https://github.com/username/repo.git`

2. **Private 저장소 인증:**
   - Personal Access Token이 설정되어 있는지 확인
   - 토큰에 `repo` 권한이 있는지 확인
   - 토큰이 만료되지 않았는지 확인

3. **GitHub Token 생성 방법:**
   ```
   GitHub → Settings → Developer settings →
   Personal access tokens → Tokens (classic) → Generate new token

   권한 선택:
   ✓ repo (전체 repo 권한)
   ```

4. **GitLab Token 생성 방법:**
   ```
   GitLab → Preferences → Access Tokens → Add new token

   권한 선택:
   ✓ read_repository
   ```

5. **환경 변수 확인:**
   ```bash
   # .env 파일에서 확인
   GIT_TOKEN=your_token_here  # 토큰이 올바르게 설정되었는지 확인
   ```

**"Repository not found" 오류:**
- 저장소 이름과 소유자가 올바른지 확인
- Private 저장소인 경우 인증 토큰이 설정되어 있는지 확인

**로컬 저장소 사용 시 권한 오류:**
```bash
# 디렉토리 권한 확인
ls -la /path/to/repo

# 필요시 권한 변경
chmod -R 755 /path/to/repo
```

## 📧 연락처

문의사항이 있으시면 이슈를 등록해주세요.
