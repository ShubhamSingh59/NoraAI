""" This code helps us to initlize the DB. We take the JSON and store it to the Chroma using langchain and Hugging Face """

import json
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_community.document_loaders import JSONLoader
from dotenv import load_dotenv
import os

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

texts = []


# Custom MetaData --> this is to match the exact id
def extract_metadata(record: dict, metadata: dict) -> dict:
    metadata["id"] = record.get("id")
    metadata["bhk"] = record.get("bhk")
    metadata["location"] = record.get("location")
    metadata["price_min"] = record.get("price_min_aed")
    return metadata


def setup_db():
    ## First check if the DB already exist or not
    if os.path.exists("./chroma_db"):
        print("Database already exists. Skipping setup.")
        return

   
    loader = JSONLoader(
        file_path="sample_properties.json",
        jq_schema=".[]",
        metadata_func=extract_metadata,
        text_content=False,
    )

    docs = loader.load()

    embeddings = HuggingFaceEndpointEmbeddings(
        model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", # Using multilingual model which helps to detect the user language
        huggingfacehub_api_token=HF_TOKEN,
        task="feature-extraction",
    )

    Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="properties",
        persist_directory="./chroma_db",
    )
