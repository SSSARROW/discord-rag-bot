# Discord RAG Bot with Guardrails System

A Discord bot that implements Retrieval-Augmented Generation (RAG) with advanced guardrails to prevent hallucinations and ensure reliable responses. The bot can process various document formats and answer questions based on the uploaded content while maintaining high response quality through comprehensive validation.

## 🌟 Features

### 🤖 RAG Capabilities
- **Multi-format Document Support**: PDF, DOCX, TXT, and more via Docling
- **Vector Database**: ChromaDB for efficient document retrieval
- **Smart Chunking**: Optimized text splitting for better context
- **Source Attribution**: Responses include references to source documents

### 🛡️ Advanced Guardrails System
- **Anti-Hallucination Protection**: Detects and prevents AI-generated misinformation
- **Response Quality Monitoring**: Real-time validation of all responses
- **Confidence Scoring**: Rates response reliability from 0.0 to 1.0
- **Content Filtering**: Blocks inappropriate or off-topic content
- **Source Grounding**: Ensures responses are based on provided documents

### 📊 Admin Features
- **Document Management**: Upload, list, and remove documents
- **Statistics Dashboard**: Monitor bot performance and quality metrics
- **Guardrail Monitoring**: Track hallucination risks and warnings
- **Comprehensive Logging**: Detailed logs for troubleshooting

### 🔧 Flexible AI Backend
- **Cloud Option** ([rag.py](rag.py)): Google Gemini 2.0 Flash for high performance
- **Local Option** ([rag_local.py](rag_local.py)): Ollama with Llama2 for privacy

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord Bot Token
- Google Gemini API Key (for cloud version) OR Ollama (for local version)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd discord-rag-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   GEMINI_API_KEY=your_gemini_api_key_here  # Only for cloud version
   ```

4. **For local version setup (optional)**
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull Llama2 model
   ollama pull llama2
   ```

5. **Run the bot**
   ```bash
   # Cloud version (recommended)
   python bot.py
   
   # Or local version
   # Modify bot.py to import from rag_local instead of rag
   ```

## 📝 Usage

### User Commands

#### `/ask <question>`
Ask any question about the uploaded documents. The bot will provide answers with quality indicators.

**Example:**
```
/ask What are the main features of the product?
```

### Admin Commands (Administrator permission required)

#### `/listdocs`
View all uploaded documents in the system.

#### `/botstats`
View comprehensive bot statistics including:
- Response quality distribution
- Hallucination risk metrics
- Guardrail warning frequency
- Performance indicators

#### `/status`
Check document processing status and system health.

#### `/rebuild`
Manually rebuild the document index (useful after bulk document changes).

#### `/removedoc`
Remove documents using an interactive dropdown menu.

### Document Upload

Admins can upload documents using the `!adddoc` command with file attachments:

```
!adddoc
[Attach your files here]
```

Supported formats: PDF, DOCX, TXT, and more.

## 🏗️ Architecture

```
User Query → RAG System → LLM Response → Guardrails Validation → Enhanced Response → User
```

### Core Components

- **[bot.py](bot.py)**: Main Discord bot with slash commands
- **[rag.py](rag.py)**: Cloud-based RAG implementation with Gemini
- **[rag_local.py](rag_local.py)**: Local RAG implementation with Ollama
- **[guardrails.py](guardrails.py)**: Comprehensive guardrails system

### Guardrails System

#### Quality Levels
- 🟢 **High Confidence**: Well-grounded, properly attributed responses
- 🟡 **Medium Confidence**: Good responses with minor uncertainty
- 🟠 **Low Confidence**: Responses requiring user verification
- 🔴 **Hallucination Risk**: Responses with strong disclaimers

#### Validation Checks
- Hallucination pattern detection
- Context grounding verification
- Source attribution requirements
- Content appropriateness filtering
- Response length optimization

## 📊 Statistics & Monitoring

The bot tracks comprehensive metrics accessible via `/botstats`:

- **Query Statistics**: Total queries and response distribution
- **Quality Metrics**: Average response quality and confidence
- **Guardrail Monitoring**: Warning frequency and risk levels
- **Performance Indicators**: System health and efficiency

All activities are logged to `bot.log` for detailed analysis.

## ⚙️ Configuration

### Environment Variables
```env
DISCORD_BOT_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key  # For cloud version
```

### Customization

#### Adjusting Confidence Thresholds
Modify confidence scoring in [`guardrails.py`](guardrails.py):

```python
def _determine_quality(self, confidence_score: float, warnings: List[str]) -> ResponseQuality:
    # Adjust these thresholds based on your needs
    if confidence_score >= 0.8:
        return ResponseQuality.HIGH_CONFIDENCE
    # ... etc
```

#### Adding Hallucination Patterns
Extend pattern detection in [`HallucinationDetector`](guardrails.py):

```python
self.hallucination_patterns = [
    r'\b(your_custom_pattern)\b',
    # ... existing patterns
]
```

## 🔧 Troubleshooting

### Common Issues

**High Hallucination Risk Rate**
- Verify document quality and relevance
- Check if source documents are comprehensive
- Consider adjusting confidence thresholds

**Low Response Quality**
- Ensure documents are properly indexed
- Verify questions are specific enough
- Check source document coverage

**Bot Not Responding**
- Check Discord bot permissions
- Verify API keys in `.env` file
- Review logs in `bot.log`

### Logging

The system provides detailed logging at multiple levels:
- **INFO**: Normal operations and query processing
- **WARNING**: Guardrail violations and quality issues
- **ERROR**: System errors and processing failures

Check `bot.log` for detailed troubleshooting information.

## 📁 Project Structure

```
discord-rag-bot/
├── bot.py                 # Main Discord bot
├── rag.py                 # Cloud RAG implementation
├── rag_local.py          # Local RAG implementation
├── guardrails.py         # Guardrails system
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── GUARDRAILS_README.md  # Detailed guardrails documentation
├── docs/                 # Document storage folder
├── chroma_db/           # Vector database
└── __pycache__/         # Python cache files
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **LangChain**: For RAG framework and document processing
- **ChromaDB**: For vector database functionality
- **Docling**: For advanced document parsing
- **Discord.py**: For Discord bot framework
- **Google Gemini**: For high-quality language model
- **Ollama**: For local AI model deployment

## 📞 Support

For issues or questions:
1. Check the logs in `bot.log`
2. Review statistics via `/botstats`
3. Consult the Guardrails Documentation
4. Open an issue on GitHub

---

**Note**: This bot includes advanced guardrails to prevent AI hallucinations and ensure response quality. All responses are validated before being sent to users, providing reliable and trustworthy information based on your documents.
