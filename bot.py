# bot.py
import os
import discord
from discord import app_commands, ui
from dotenv import load_dotenv
from rag import get_rag_bot, build_index
import logging
from datetime import datetime

# Ensure docs folder exists
os.makedirs("docs", exist_ok=True)
docs_folder = "docs"

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Setup bot
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Build RAG index and load QA bot
build_index()
qa = get_rag_bot()

# Statistics tracking
bot_stats = {
    'total_queries': 0,
    'high_confidence_responses': 0,
    'medium_confidence_responses': 0,
    'low_confidence_responses': 0,
    'hallucination_risks': 0,
    'guardrail_warnings': 0
}


# ---------------- Permission Helpers ---------------- #
def _user_is_admin(user: discord.abc.User) -> bool:
    """Return True if the user has Administrator permission in this guild."""
    try:
        # For guild members, check guild permissions
        return bool(getattr(user.guild_permissions, "administrator", False))
    except Exception:
        return False

def _interaction_is_admin(interaction: discord.Interaction) -> bool:
    return _user_is_admin(interaction.user)

@bot.event
async def on_ready():
    print(f" Logged in as {bot.user}")
    try:
        synced = await tree.sync()
        print(f" Synced {len(synced)} slash commands")
    except Exception as e:
        print(f" Failed to sync commands: {e}")

# ---------------- Slash Commands ---------------- #

@tree.command(name="ask", description="Ask a question to the RAG bot")
async def ask_command(interaction: discord.Interaction, query: str):
    try:
        # Log the query
        logger.info(f"Query from {interaction.user}: {query[:100]}...")
        bot_stats['total_queries'] += 1
        
        # Get response with guardrails
        result = qa.invoke(query)
        response = result['result']
        
        # Extract guardrail information
        guardrail_info = result.get('guardrail_result', {})
        quality = guardrail_info.get('quality', 'unknown')
        confidence = guardrail_info.get('confidence_score', 0.0)
        warnings = guardrail_info.get('warnings', [])
        
        # Update statistics
        if quality == 'high_confidence':
            bot_stats['high_confidence_responses'] += 1
        elif quality == 'medium_confidence':
            bot_stats['medium_confidence_responses'] += 1
        elif quality == 'low_confidence':
            bot_stats['low_confidence_responses'] += 1
        elif quality == 'hallucination_risk':
            bot_stats['hallucination_risks'] += 1
        
        if warnings:
            bot_stats['guardrail_warnings'] += 1
            logger.warning(f"Guardrail warnings for query '{query[:50]}...': {warnings}")
        
        # Log response quality
        logger.info(f"Response quality: {quality}, Confidence: {confidence:.2f}")
        
        # Send response
        await interaction.response.send_message(response)
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing query '{query[:50]}...': {error_msg}")
        
        if "quota" in error_msg.lower() or "exceeded" in error_msg.lower():
            await interaction.response.send_message(" Sorry, the AI quota has been exceeded. Please try again later or contact the bot admin.")
        else:
            await interaction.response.send_message(f" An error occurred: {error_msg}")

# Remove the adddoc_command function

# --- Dropdown for previewing docs ---
class PreviewDocDropdown(ui.Select):
    def __init__(self, docs):
        options = [discord.SelectOption(label=doc, value=doc) for doc in docs]
        super().__init__(placeholder="Select a document to preview...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        filename = self.values[0]
        file_path = os.path.join(docs_folder, filename)

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(500)  # show first 500 chars
            await interaction.response.edit_message(
                content=f" **{filename}** Preview:\n```{content}...```",
                view=None
            )
        else:
            await interaction.response.edit_message(content=f" File `{filename}` not found.", view=None)

class PreviewDocView(ui.View):
    def __init__(self, docs):
        super().__init__()
        self.add_item(PreviewDocDropdown(docs))

@app_commands.default_permissions(administrator=True)
@tree.command(name="listdocs", description="List and preview available documents (admins only)")
async def listdocs_command(interaction: discord.Interaction):
    if not _interaction_is_admin(interaction):
        await interaction.response.send_message(" You must be an admin to use this command.", ephemeral=True)
        return
    if os.path.exists(docs_folder):
        files = os.listdir(docs_folder)
        if not files:
            await interaction.response.send_message(" No documents found in the docs folder.")
            return
        view = PreviewDocView(files)
        await interaction.response.send_message(" Choose a document to preview:", view=view)
    else:
        await interaction.response.send_message(" Docs folder does not exist yet.")

@app_commands.default_permissions(administrator=True)
@tree.command(name="botstats", description="View bot statistics and guardrail information (admins only)")
async def botstats_command(interaction: discord.Interaction):
    if not _interaction_is_admin(interaction):
        await interaction.response.send_message(" You must be an admin to use this command.", ephemeral=True)
        return
    
    total = bot_stats['total_queries']
    if total == 0:
        await interaction.response.send_message(" **Bot Statistics**\nNo queries processed yet.")
        return
    
    # Calculate percentages
    high_pct = (bot_stats['high_confidence_responses'] / total) * 100
    medium_pct = (bot_stats['medium_confidence_responses'] / total) * 100
    low_pct = (bot_stats['low_confidence_responses'] / total) * 100
    risk_pct = (bot_stats['hallucination_risks'] / total) * 100
    warning_pct = (bot_stats['guardrail_warnings'] / total) * 100
    
    stats_message = f""" **Bot Statistics & Guardrail Monitoring**

**Query Statistics:**
• Total Queries: {total}
• High Confidence: {bot_stats['high_confidence_responses']} ({high_pct:.1f}%)
• Medium Confidence: {bot_stats['medium_confidence_responses']} ({medium_pct:.1f}%)
• Low Confidence: {bot_stats['low_confidence_responses']} ({low_pct:.1f}%)
• Hallucination Risks: {bot_stats['hallucination_risks']} ({risk_pct:.1f}%)

**Guardrail Monitoring:**
• Responses with Warnings: {bot_stats['guardrail_warnings']} ({warning_pct:.1f}%)

**Quality Metrics:**
• Average Response Quality: {' Good' if high_pct > 60 else 'Moderate' if high_pct > 30 else ' Needs Attention'}
• Hallucination Risk Level: {' Low' if risk_pct < 10 else ' Medium' if risk_pct < 25 else ' High'}

*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"""
    
    await interaction.response.send_message(stats_message)

# --- Dropdown for removing docs ---
class RemoveDocDropdown(ui.Select):
    def __init__(self, docs):
        options = [discord.SelectOption(label=doc, value=doc) for doc in docs]
        super().__init__(placeholder="Select a document to remove...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if not _interaction_is_admin(interaction):
            await interaction.response.edit_message(content=" Only admins can remove documents.", view=None)
            return
        filename = self.values[0]
        file_path = os.path.join(docs_folder, filename)

        if os.path.exists(file_path):
            os.remove(file_path)
            build_index(docs_folder)
            await interaction.response.edit_message(content=f" `{filename}` removed and index updated.", view=None)
        else:
            await interaction.response.edit_message(content=f" File `{filename}` not found.", view=None)

class RemoveDocView(ui.View):
    def __init__(self, docs):
        super().__init__()
        self.add_item(RemoveDocDropdown(docs))

@app_commands.default_permissions(administrator=True)
@tree.command(name="removedoc", description="Remove a document by selecting from a list (admins only)")
async def removedoc_command(interaction: discord.Interaction):
    if not _interaction_is_admin(interaction):
        await interaction.response.send_message(" You must be an admin to use this command.", ephemeral=True)
        return
    if os.path.exists(docs_folder):
        files = os.listdir(docs_folder)
        if not files:
            await interaction.response.send_message(" No documents to remove.")
            return
        view = RemoveDocView(files)
        await interaction.response.send_message(" Choose a document to remove:", view=view)
    else:
        await interaction.response.send_message(" Docs folder does not exist yet.")

@bot.event
async def on_message(message):
    print(f"Message received: {message.content} from {message.author}")
    if message.author == bot.user:
        return
    
    if message.content.lower() == "!adddoc" and message.attachments:
        # Gate by admin only
        if not _user_is_admin(message.author):
            await message.channel.send(" Only admins can add documents.")
            return
        for attachment in message.attachments:
            file_path = os.path.join(docs_folder, attachment.filename)
            await attachment.save(file_path)
            print(f" Saved {attachment.filename}")
        build_index(docs_folder)
        await message.channel.send(" Document(s) added and indexed!")
    elif message.content.lower() == "!adddoc" and not message.attachments:
        # Still enforce admin check to avoid leaking usage to non-admins
        if not _user_is_admin(message.author):
            await message.channel.send(" Only admins can add documents.")
        else:
            await message.channel.send(" Please attach a file with `!adddoc`.")
    
    # Removed process_commands since we're not using prefix commands

bot.run(TOKEN)
