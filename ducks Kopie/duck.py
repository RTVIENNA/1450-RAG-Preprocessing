# -*- coding: utf-8 -*-
"""God_of_ducks_and_lamas.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/github/RTVIENNA/1450-RAG-Preprocessing/blob/main/God_of_ducks_and_lamas.ipynb

# The 1450 Navigator 🧭

🕵🏻 Agentic RAG with 🦙 Llama 3.2 3B

The running ducks and the smart LAMA

🎯 Our goal is to create a system that answers questions using a knowledge base focused on medical information. If the retrieved documents don't contain the answer, the application will fall back to web search for additional context.

Stack:

🦆📄 Docling: Docling simplifies document processing, parsing diverse formats — including advanced PDF understanding — and providing seamless integrations with the gen AI ecosystem.
Parsing of multiple document formats incl. PDF, DOCX, XLSX, HTML, images, and more

🏗️ Haystack: open-source LLM orchestration framework that streamlines the development of your LLM applications.

🦙 Llama-3.2-3B-Instruct: small and good Language Model.

🦆🌐 DuckDuckGo API Websearch to search results on the Web.

Make sure that the T4 GPU is running
"""
#======================================================================================================================

#======================================================================================================================
# ! pip install docling

# ! pip install haystack-ai duckduckgo-api-haystack transformers sentence-transformers datasets

import os #3
from transformers import AutoModelForSequenceClassification #3

import gdown #4
from docling.document_converter import DocumentConverter #4
from haystack import Document #4
from haystack.document_stores.in_memory import InMemoryDocumentStore #4
from haystack.components.embedders import SentenceTransformersDocumentEmbedder #4

import torch #6
from haystack.components.generators import HuggingFaceLocalGenerator #6

from haystack.components.embedders import SentenceTransformersTextEmbedder #8
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever #8

from haystack.components.builders import PromptBuilder #9

from haystack.components.routers import ConditionalRouter #10

from duckduckgo_api_haystack import DuckduckgoApiWebSearch #11

from haystack.components.joiners import BranchJoiner #14
prompt_joiner  = BranchJoiner(str)

from haystack import Pipeline #14

"""Access to external Documents that are saved in a google drive. The data is cleaned/ chuncked and embedded"""
#=================================================================================================
#=================================================================================================

import logging

logging.basicConfig(level=logging.INFO)

logging.info("Step 1: Downloading files from Google Drive...")
# Code for downloading files
logging.info("Step 2: Processing downloaded files...")
# Code for processing files
logging.info("Step 3: Initializing document store...")
# Code for initializing document store
######
#########
from tqdm import tqdm
import time

# Example: Simulating file processing
files = ["file1.pdf", "file2.pdf", "file3.pdf"]
for file in tqdm(files, desc="Processing files"):
    time.sleep(1)  # Simulate processing time


#======================================================================================================================

#======================================================================================================================
# 1. Download files from Google Drive
url = "https://drive.google.com/drive/u/0/folders/1YrBIqbbi5uXjR-fuEAMBHL-TwpjtViXu"
output_dir = "1450_files"
gdown.download_folder(url, quiet=True, output=output_dir)

# 2. Process each downloaded file
import os
for filename in os.listdir(output_dir):
    if filename.endswith(".pdf"):  # Adjust file extension if needed
        filepath = os.path.join(output_dir, filename)

        # 3. Convert the PDF file
        converter = DocumentConverter()
        result = converter.convert(filepath)
        converted_text = result.document.export_to_markdown()
        print(result.document.export_to_markdown())

        # 4. Create a Haystack Document object
        doc = Document(content=converted_text, meta={"source": filepath})

# 3. Einrichten des In-Memory-Dokumentenspeichers
document_store = InMemoryDocumentStore()

# 4. Initialisieren und Aufwärmen des Document Embedder
doc_embedder = SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
doc_embedder.warm_up()

# 5. Embedding des Dokuments und Schreiben in den Dokumentenspeicher
docs_with_embeddings = doc_embedder.run([doc])
document_store.write_documents(docs_with_embeddings["documents"])
#======================================================================================================================

#======================================================================================================================

from haystack_integrations.components.generators.ollama import OllamaGenerator

generator = OllamaGenerator(
    model="llama3.2:3b-instruct-q4_K_M",  # Das gewünschte Ollama-Modell
    url="http://localhost:11434",         # URL, unter der Ollama erreichbar ist
    generation_kwargs={
        "num_predict": 100,               # Beispielwert – passe ihn nach Bedarf an
        "temperature": 0.9,               # Beispielwert – passe ihn nach Bedarf an
    }, 
)
#11434
generator._client._client.timeout = 600
#======================================================================================================================

#======================================================================================================================

"""Build the 🕵🏻 Agentic RAG Pipeline

Retrieval part- initialize the components to use for the initial retrieval phase.
"""

text_embedder = SentenceTransformersTextEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
retriever = InMemoryEmbeddingRetriever(document_store, top_k=5)

"""Prompt template
Let's define the first prompt template, which instructs the model to:

answer the query based on the retrieved documents, if possible
reply with 'no_answer', otherwise
"""

prompt_template = """
<|begin_of_text|><|start_header_id|>user<|end_header_id|>

Answer the following query given the documents.
If the answer is not contained within the documents reply with 'no_answer'.
If the answer is contained within the documents, start the answer with "FROM THE KNOWLEDGE BASE: ".

Documents:
{% for document in documents %}
  {{document.content}}
{% endfor %}

Query: {{query}}<|eot_id|>

<|start_header_id|>assistant<|end_header_id|>
"""

prompt_builder = PromptBuilder(template=prompt_template)

"""Conditional Router
This is the component that will perform data routing, depending on the reply given by the Language Model.
"""

routes = [
    {
        "condition": "{{'no_answer' in replies[0]}}",
        "output": "{{query}}",
        "output_name": "go_to_websearch",
        "output_type": str,
    },
    {
        "condition": "{{'no_answer' not in replies[0]}}",
        "output": "{{replies[0]}}",
        "output_name": "answer",
        "output_type": str,
    },
]

router = ConditionalRouter(routes)

router.run(replies=["this is the answer!"])

router.run(replies=["no_answer"], query="my query")

"""WEB search with duckduckgo"""

websearch = DuckduckgoApiWebSearch(top_k=5)

# Perform a search
results = websearch.run(query="Triage Algortihm?")

# Access the search results
documents = results["documents"]
links = results["links"]

print("Found documents:")
for doc in documents:
    print(f"Content: {doc.content}")

print("\nSearch Links:")
for link in links:
    print(link)

"""Prompt template after Web search"""

prompt_template_after_websearch = """
<|begin_of_text|><|start_header_id|>user<|end_header_id|>

Answer the following query given the documents retrieved from the web.
Start the answer with "FROM THE WEB: ".

Documents:
{% for document in documents %}
  {{document.content}}
{% endfor %}

Query: {{query}}<|eot_id|>

<|start_header_id|>assistant<|end_header_id|>
"""

prompt_builder_after_websearch = PromptBuilder(template=prompt_template_after_websearch)

"""Assembling the Pipeline"""
#======================================================================================================================

#======================================================================================================================
prompt_joiner  = BranchJoiner(str)

pipe = Pipeline()
pipe.add_component("text_embedder", text_embedder)
pipe.add_component("retriever", retriever)
pipe.add_component("prompt_builder", prompt_builder)
pipe.add_component("prompt_joiner", prompt_joiner)
pipe.add_component("llm", generator)
pipe.add_component("router", router)
pipe.add_component("websearch", websearch)
pipe.add_component("prompt_builder_after_websearch", prompt_builder_after_websearch)

pipe.connect("text_embedder", "retriever")
pipe.connect("retriever", "prompt_builder.documents")
pipe.connect("prompt_builder", "prompt_joiner")
pipe.connect("prompt_joiner", "llm")
pipe.connect("llm.replies", "router.replies")
pipe.connect("router.go_to_websearch", "websearch.query")
pipe.connect("router.go_to_websearch", "prompt_builder_after_websearch.query")
pipe.connect("websearch.documents", "prompt_builder_after_websearch.documents")
pipe.connect("prompt_builder_after_websearch", "prompt_joiner")

"""Agentic RAG in action! 🔎"""
#======================================================================================================================

#======================================================================================================================

def get_answer(query):
  result = pipe.run({"text_embedder": {"text": query}, "prompt_builder": {"query": query}, "router": {"query": query}})
  print(result["router"]["answer"])

query = "What is the Manchester Triage Algorithm ?"

get_answer(query)

query = "I have fever, what should I do ?"

get_answer(query)

query = "I have chest pain?"

get_answer(query)