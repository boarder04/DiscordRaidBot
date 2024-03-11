import asyncio
import random
import discord
from discord import app_commands, Interaction
from discord.app_commands import Range
import config
from datetime import datetime, timedelta

class RandomBidView(discord.ui.View):
    def __init__(self, timeout: int):
        self.user_bids = {}  # Store user bids as a dict
        super().__init__(timeout=timeout)

    async def handle_bid(self, interaction: Interaction, bid_type: str):
        user_id = interaction.user.id  # Use user ID to uniquely identify users

        if user_id in self.user_bids:
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.red(),
                    description=f'You have already placed a bid as **{self.user_bids[user_id]}**!'
                ),
                ephemeral=True
            )
        else:
            self.user_bids[user_id] = bid_type
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.green(),
                    description=f'You have successfully bid as **{bid_type}**.'
                ),
                ephemeral=True
            )

    @discord.ui.button(label='Priority Roll', custom_id='raidMain_bid_join')
    async def join_main(self, interaction: Interaction, button: discord.ui.Button):
        await self.handle_bid(interaction, "PRIORITY")

    @discord.ui.button(label='Standard Roll', custom_id='alt_bid_join')
    async def join_alt(self, interaction: Interaction, button: discord.ui.Button):
        await self.handle_bid(interaction, "Standard Roll")

    @discord.ui.button(label='Leave', custom_id='bid_leave')
    async def leave(self, interaction: Interaction, button: discord.ui.Button):
        user_id = interaction.user.id

        if user_id not in self.user_bids:
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.red(), 
                    description='You have not joined the bid!'
                ),
                ephemeral=True
            )
        else:
            bid_type = self.user_bids.pop(user_id)
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.green(), 
                    description=f'You have left the bid as **{bid_type}**.'
                ),
                ephemeral=True
            )

class PlatBidView(discord.ui.View):
    def __init__(self, timeout: int):
        super().__init__(timeout=timeout)
        self.bids = {}
        self.last_bid_time = datetime.now()  # Track the time of the last bid
        self.session_active = False  # Flag to indicate if a session is active
        self.priority_winners = set()  # Set to store users who have won a priority bid
        self.item_winners = {}  # Dictionary to store item winners
        self.standard_roll_counts = {}  # Dictionary to store the count of standard rolls won by each user
        self.session_items = []  # List to store session items and winners

    async def check_session_timeout(self):
        while True:
            await asyncio.sleep(3600)  # Check every hour

            # Calculate elapsed time since last bid
            elapsed_time = datetime.now() - self.last_bid_time

            # If more than an hour has passed since the last bid and session is active, end the session
            if elapsed_time > timedelta(hours=1) and self.session_active:
                self.session_active = False
                self.bids.clear()  # Clear bids
                self.priority_winners.clear()  # Clear priority winners
                self.item_winners.clear()  # Clear item winners
                self.standard_roll_counts.clear()  # Clear standard roll counts
                print("Session ended due to inactivity.")
                await self.output_session_summary()

    @discord.ui.button(label='Bid', style=discord.ButtonStyle.green, custom_id='bid_button')
    async def bid_button(self, interaction: Interaction, button: discord.ui.Button):
        if self.session_active:
            modal = PlatBidModal(self.bids, self.priority_winners)
            await interaction.response.send_modal(modal)
            self.last_bid_time = datetime.now()  # Update last bid time
        else:
            await interaction.response.send_message("Bid session is not active.", ephemeral=True)

    @discord.ui.button(label='Leave Bid', style=discord.ButtonStyle.red, custom_id='leave_bid_button')
    async def leave_bid_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.display_name in self.bids:
            del self.bids[interaction.user.display_name]
            await interaction.response.send_message("You have left the bid.", ephemeral=True)
        else:
            await interaction.response.send_message("You did not place a bid.", ephemeral=True)

    def get_sorted_bids(self):
        return sorted(self.bids.items(), key=lambda x: x[1], reverse=True)

    async def output_session_summary(self):
        """Output session summary."""
        summary_embed = discord.Embed(
            color=discord.Color.blue(),
            title="Session Summary",
            description="Items and Winners"
        )

        # Add items and winners to the embed
        for item, winner in self.session_items:
            summary_embed.add_field(name=item, value=f"Winner: {winner}", inline=False)

        summary_embed.add_field(name="Total Items", value=len(self.session_items))
        unique_winners = len(set(winner for _, winner in self.session_items))
        summary_embed.add_field(name="Total Unique Winners", value=unique_winners)

        # Find the channel where the session was conducted
        channel = self.message.channel if hasattr(self, 'message') else None

        if channel:
            await channel.send(embed=summary_embed)

class PlatBidModal(discord.ui.Modal):
    def __init__(self, bids, priority_winners):
        super().__init__(title=f"Place Your Bid (Minimum Bid: {CustomBot.min_bid:,})")
        self.bids = bids
        self.priority_winners = priority_winners

    bid_amount = discord.ui.TextInput(label="Bid Amount", placeholder="Enter your bid amount here")

    async def on_submit(self, interaction: Interaction):
        bid_amount_str = self.bid_amount.value.replace(",", "")
        try:
            bid_amount = int(bid_amount_str)
        except ValueError:
            await interaction.response.send_message("Please enter a valid number for the bid amount.", ephemeral=True)
            return

        if bid_amount < CustomBot.min_bid:
            await interaction.response.send_message(f"Your bid must be at least {CustomBot.min_bid}.", ephemeral=True)
            return

        self.bids[interaction.user.display_name] = bid_amount
        await interaction.response.send_message(f"Your bid of {bid_amount} has been placed.", ephemeral=True)

        # Check if user won a priority bid
        if interaction.user.display_name not in self.priority_winners:
            self.priority_winners.add(interaction.user.display_name)
            # Disable the priority button if the user won a priority bid
            self.view.children[0].disabled = True

class CustomBot(discord.Client):
    min_bid = 1  # Class attribute for minimum bid

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents, help_command=None)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.tree.clear_commands(guild=None)
        self.tree.add_command(start_random)
        self.tree.add_command(start_bids)
        self.tree.add_command(set_min_bid)
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.session_timeout_task = asyncio.create_task(self.check_session_timeouts())

    async def check_session_timeouts(self):
        """Check for session timeouts."""
        while True:
            await asyncio.sleep(3600)  # Check every hour for session timeout
            for guild in self.guilds:
                for view in guild.ui.views:
                    if isinstance(view, PlatBidView) and view.session_active:
                        elapsed_time = datetime.now() - view.last_bid_time
                        if elapsed_time > timedelta(hours=1):
                            view.session_active = False
                            view.bids.clear()  # Clear bids
                            view.priority_winners.clear()  # Clear priority winners
                            view.item_winners.clear()  # Clear item winners
                            view.standard_roll_counts.clear()  # Clear standard roll counts
                            print("Session ended due to inactivity.")
                            await view.output_session_summary()

@bot.tree.command(name='random')
@app_commands.guild_only()
@app_commands.describe(item='The name of the item', classes='Who can roll on the item', time='The time in seconds until the end of the bid')
async def start_random(interaction: Interaction, item: str, classes: str, time: Range[int, 1, 600]):
    """Starts a bid for an item."""

    view = RandomBidView(time)
    embed = discord.Embed(
        color=discord.Color.blue(),
        description=f'Now rolling: **{item}**!\n\nThe following may bid:\n**{classes}**'
    )

    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(time)
    view.stop()

    # Separate priority rolls and standard rolls
    priority_rolls = [f'{interaction.guild.get_member(user_id).display_name} ({bid_type})' for user_id, bid_type in view.user_bids.items() if interaction.guild.get_member(user_id) and bid_type == 'Priority Roll']
    standard_rolls = [f'{interaction.guild.get_member(user_id).display_name} ({bid_type} - {view.standard_roll_counts.get(user_id, 0)})' for user_id, bid_type in view.user_bids.items() if interaction.guild.get_member(user_id) and bid_type == 'Standard Roll']

    # Shuffle both lists independently
    random.shuffle(priority_rolls)
    random.shuffle(standard_rolls)

    # Concatenate lists with priority rolls on top
    sorted_bids = priority_rolls + standard_rolls

    winners_text = '\n'.join(sorted_bids) if sorted_bids else "No users joined!"
    embed.description += f'\n\n**Results**:\n{winners_text}'

    # Disable all buttons after the bidding period is over
    for item in view.children:
        item.disabled = True

    await interaction.edit_original_response(embed=embed, view=view)

@bot.tree.command(name='bid')
@app_commands.guild_only()
@app_commands.describe(item='The name of the item', classes='Who can bid on the item', time='The time in seconds until the end of the bid \n 30 minute or 1800s max.')
async def start_bids(interaction: Interaction, item: str, classes: str, time: Range[int, 1, 1800]):
    view = PlatBidView(time)
    embed = discord.Embed(
        color=discord.Color.blue(),
        description=f'Now bidding: **{item}**!\n\nThe following may bid:\n**{classes}**'
    )

    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(time)
    view.stop()

    sorted_bids = view.get_sorted_bids()

    # Determine the payment amount
    if len(sorted_bids) >= 2:
        payment_amount = sorted_bids[1][1] + 1  # Second place bid + 1
    elif len(sorted_bids) == 1:
        payment_amount = bot.min_bid + 1  # Minimum bid + 1 if only one bid
    else:
        payment_amount = None  # No bids were placed

    winners_text = '\n'.join(f'{user} bid {amount:,}' for user, amount in sorted_bids)
    payment_text = f"Payment amount: {payment_amount:,}" if payment_amount is not None else "No bids were placed!"

    embed.description += f'\n\n**Results**:\n{winners_text}\n\n{payment_text}'

    for item in view.children:
        item.disabled = True

    await interaction.edit_original_response(embed=embed, view=view)

@bot.tree.command(name='minbid')
@app_commands.describe(min_bid='The minimum bid amount')
async def set_min_bid(interaction: Interaction, min_bid: int):
    """Sets the minimum bid amount."""
    CustomBot.min_bid = max(1, min_bid)
    await interaction.response.send_message(f"Minimum bid set to {CustomBot.min_bid}.", ephemeral=True)

@bot.tree.command(name='changewinner')
@app_commands.describe(item='The name of the item', current_winner='The current winner of the item', new_winner='The new winner of the item')
async def change_winner(interaction: Interaction, item: str, current_winner: str, new_winner: str):
    """Changes the winner of an item."""
    # Check if the current winner exists
    if current_winner not in bot.item_winners.get(item, []):
        await interaction.response.send_message(f"{current_winner} is not the current winner of {item}.", ephemeral=True)
        return

    # Change the winner to the new winner
    bot.item_winners[item] = new_winner
    await interaction.response.send_message(f"The winner of {item} has been changed from {current_winner} to {new_winner}.", ephemeral=True)

bot.run(config.TOKEN)