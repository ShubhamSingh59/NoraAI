# Nora AI - Real Estate WhatsApp Agent

Nora is a RAG-powered WhatsApp real estate assistant built with FastAPI, LangChain, and ChromaDB. It supports English, Hindi, Hinglish, and Arabic while ensuring responses are grounded only in the provided property inventory.

---

## Local Setup

### 1. Clone the Repository

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file using `.env.example` as a template.

Required environment variables:

```env
HF_TOKEN=your_huggingface_token
```

### 5. Run Tests

```bash
pytest test_main.py -v
```

### 6. Start the Application

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

---

## Docker

Build the image:

```bash
docker build -t nora-ai .
```

Run the container:

```bash
docker run -p 8000:8000 --env-file .env nora-ai
```

---

## Environment Variables

See `.env.example`.

Required:

```env
HF_TOKEN=
```

---

## LLM Provider & Model

- Provider: Hugging Face
- Model for Embedding: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Model for LLM: `Qwen/Qwen2.5-7B-Instruct`

### Why this model?

- Strong multilingual support
- Cost-effective deployment as it is free to use
- Easy integration with LangChain

---

### Hallucination Prevention

- Responses are generated only from retrieved inventory data.
- Retrieved context is injected into the prompt.
- Missing information is never fabricated.
- No-match scenarios return a fallback response instead of generating unsupported property recommendations.

---

## Demo Video

Recording Link:

```
<loom-link>
```

---

## Future Improvements

- WhatsApp Business API integration
- Better lead scoring and analytics
- Better langauage detaction and swtiching
- Better way of storing the chat history