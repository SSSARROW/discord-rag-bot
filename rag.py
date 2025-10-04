# rag.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from docling.document_converter import DocumentConverter
from langchain.schema import Document
from guardrails import GuardrailSystem, create_safe_response
import logging

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup embeddings + vector DB (using local HuggingFace embeddings - free!)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

# Initialize guardrail system
guardrail_system = GuardrailSystem()

def load_file(file_path):
    """Use Docling to parse PDF, DOCX, TXT, or supported formats"""
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        # Docling handles PDF, DOCX, PPTX, images, etc.
        converter = DocumentConverter()
        result = converter.convert(file_path)
        return result.document.export_to_markdown()

def build_index(docs_folder="docs"):
    """Scan folder and rebuild vector DB"""
    all_docs = []

    if not os.path.exists(docs_folder):
        os.makedirs(docs_folder)

    for file_name in os.listdir(docs_folder):
        file_path = os.path.join(docs_folder, file_name)
        if os.path.isfile(file_path):
            print(f"    Parsing {file_name}")
            content = load_file(file_path)
            if content.strip():
                # Wrap in LangChain Document
                all_docs.append(Document(page_content=content, metadata={"source": file_name}))

    if all_docs:
        # Smaller chunks for local models with limited context
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Smaller for local models
            chunk_overlap=200  # Better overlap for continuity
        )
        splits = splitter.split_documents(all_docs)
        db.reset_collection()
        db.add_documents(splits)
        print(" DB updated with latest docs.")
    else:
        print(" No docs found.")

def get_rag_bot():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",  # Gemini 2.0 Flash Live model
        google_api_key=GEMINI_API_KEY,
        max_tokens=2000,  # Output token limit
        temperature=0.1,
        max_retries=3,
    )
    
    # Enhanced system prompt with anti-hallucination instructions
    template = f"""You are a helpful Discord bot that answers questions based on the provided documents. 

Context from documents:
{{context}}

Question: {{question}}

{guardrail_system.get_enhanced_prompt_instructions()}

Instructions:
- Be friendly and conversational, like a Discord bot
- Keep responses concise but informative (under 2000 characters when possible)
- If the question can't be answered from the documents, say so politely
- Use Discord-friendly formatting (emojis, bullet points if helpful)
- Reference the source documents when relevant
- Be helpful and engaging!
- Always ground your responses in the provided context
- Use phrases like "According to the document" or "Based on the provided context"
- If uncertain, use phrases like "The document suggests" or "It appears that"
- Never make up information not present in the context

Answer:"""
    
    QA_PROMPT = PromptTemplate(
        template=template, 
        input_variables=["context", "question"]
    )
    
    # Take advantage of context - retrieve fewer documents for smaller models
    retriever = db.as_retriever(search_kwargs={"k": 4})
    
    # Create the base RAG chain
    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": QA_PROMPT}
    )
    
    # Wrap with guardrails
    return GuardedRAGBot(rag_chain, guardrail_system)

class GuardedRAGBot:
    """RAG bot with integrated guardrails for hallucination prevention"""
    
    def __init__(self, rag_chain, guardrail_system):
        self.rag_chain = rag_chain
        self.guardrail_system = guardrail_system
        self.logger = logging.getLogger(__name__)
    
    def invoke(self, query: str) -> dict:
        """Invoke the RAG bot with guardrail validation"""
        try:
            # Get response from RAG chain
            result = self.rag_chain.invoke(query)
            response = result['result']
            source_documents = result.get('source_documents', [])
            
            # Extract context from source documents
            context = "\n\n".join([doc.page_content for doc in source_documents])
            
            # Run guardrail validation
            guardrail_result = self.guardrail_system.validate_response(
                response=response,
                question=query,
                context=context,
                source_documents=[doc.page_content for doc in source_documents]
            )
            
            # Log validation results
            self.logger.info(f"Guardrail validation - Quality: {guardrail_result.quality.value}, "
                           f"Confidence: {guardrail_result.confidence_score:.2f}, "
                           f"Warnings: {len(guardrail_result.warnings)}")
            
            if guardrail_result.warnings:
                self.logger.warning(f"Guardrail warnings: {guardrail_result.warnings}")
            
            # Create safe response
            safe_response = create_safe_response(response, guardrail_result)
            
            # Return enhanced result with guardrail information
            return {
                'result': safe_response,
                'source_documents': source_documents,
                'guardrail_result': {
                    'quality': guardrail_result.quality.value,
                    'confidence_score': guardrail_result.confidence_score,
                    'warnings': guardrail_result.warnings,
                    'suggestions': guardrail_result.suggestions,
                    'source_coverage': guardrail_result.source_coverage
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in GuardedRAGBot: {str(e)}")
            return {
                'result': f" An error occurred while processing your question: {str(e)}",
                'source_documents': [],
                'guardrail_result': {
                    'quality': 'error',
                    'confidence_score': 0.0,
                    'warnings': [f"System error: {str(e)}"],
                    'suggestions': ["Please try rephrasing your question"],
                    'source_coverage': 0.0
                }
            }
