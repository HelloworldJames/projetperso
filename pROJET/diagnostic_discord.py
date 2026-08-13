import os

import discord
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")


class DiagnosticBot(discord.Client):

    async def on_ready(self):

        print()
        print("=" * 60)
        print("IDENTITE DU BOT UTILISE PAR PYTHON")
        print("=" * 60)

        print(f"Nom du bot : {self.user}")
        print(f"Application ID : {self.application_id}")
        print(f"Bot User ID : {self.user.id}")

        print()
        print("Serveurs visibles :", len(self.guilds))

        for guild in self.guilds:
            print(f"- {guild.name} : {guild.id}")

        print("=" * 60)

        await self.close()


bot = DiagnosticBot(
    intents=discord.Intents.default()
)

bot.run(TOKEN)