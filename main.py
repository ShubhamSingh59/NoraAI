from fastapi import FastAPI, HTTPException
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from dotenv import load_dotenv
import os
from schemas import WebhookRequest, AgentResponse
from agent import noraResponse
import json
from database import setup_db

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

app = FastAPI(title="Nora AI")

# Build the DB
setup_db()

# Conneting to our DB and setting a retriever
embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    huggingfacehub_api_token=HF_TOKEN,
    task="feature-extraction",
)

vectorDB = Chroma(
    collection_name="properties",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
)

retriever = vectorDB.as_retriever(search_kwargs={"k": 3})

# Simple a dict to track the converstion history
memoryStore = {}


@app.get("/")
def root():
    return {"Details": "Server is Running"}


# Our main webhook
@app.post("/webhook")
async def handleWebhook(request: WebhookRequest):
    # unique ID for user
    sessionId = f"{request.client_id}_{request.from_}"
    userText = request.message.text

    # look for the history if not found initlize it
    if sessionId not in memoryStore:
        memoryStore[sessionId] = []

    session = memoryStore[sessionId]
    historyText = "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in memoryStore[sessionId]]
    )

    search_query = f"{historyText} \n User: {userText}"
    matchedData = retriever.invoke(search_query)

    ## Make the conext for our agent using matchedData
    contextText = "\n---\n".join(data.page_content for data in matchedData)

    # calling the our agent

    try:
        output = noraResponse(
            inputText=userText, historyText=historyText, contextText=contextText
        )
        output.lead.phone = request.from_
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Agent failed to parse response: {str(e)}"
        )

    ## This is to fix the golden visa issue (do not trust to the LM)
    budget = output.lead.budget_aed
    if budget is not None and budget >= 2_000_000:
        output.lead.golden_visa_eligible = True
        if "golden visa" not in output.reply.lower():
            output.reply += "\n\nAlso, great news — with a budget of AED {:,}, you qualify for the UAE Golden Visa! 🇦🇪".format(
                budget
            )
    else:
        output.lead.golden_visa_eligible = False

    # update the history
    memoryStore[sessionId].append({"role": "User", "content": userText})
    memoryStore[sessionId].append({"role": "Nora", "content": output.reply})

    return output.model_dump()
