import asyncio
import random
import discord
from discord import app_commands, Interaction
from discord.app_commands import Range
import config
import uuid

class PlatBidView(discord.ui.View):
    def __init__(self, timeout: int):
        super().__init__(timeout=timeout)
        self.bids = {}

    @discord.ui.button(label='Bid', style=discord.ButtonStyle.green, custom_id='bid_button')
    async def bid_button(self, interaction: Interaction, button: discord.ui.Button):
        modal = PlatBidModal(self.bids)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label='Leave Bid', style=discord.ButtonStyle.red, custom_id='leave_bid_button')
    async def leave_bid_button(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.display_name in self.bids:
            del self.bids[interaction.user.display_name]
            await interaction.response.send_message("You have left the bid.", ephemeral=True)
        else:
            await interaction.response.send_message("You did not place a bid.", ephemeral=True)

    def get_sorted_bids(self):
        return sorted(self.bids.items(), key=lambda x: x[1], reverse=True)

class PlatBidModal(discord.ui.Modal):
    def __init__(self, bids):
        super().__init__(title=f"Place Your Bid (Minimum Bid: {CustomBot.min_bid:,})")
        self.bids = bids

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

class RandomBidView(discord.ui.View):
    def __init__(self, timeout: int, initiator_id: int, auction_id: str, previous_priority_winners: set):
        self.user_bids = {}
        self.initiator_id = initiator_id
        self.auction_id = auction_id
        self.previous_priority_winners = previous_priority_winners
        self.winners_dropdown = None
        super().__init__(timeout=timeout)

    async def handle_bid(self, interaction: Interaction, bid_type: str):
        user_id = interaction.user.id  

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
        user_id = interaction.user.id
        if user_id in self.previous_priority_winners:
            await interaction.response.send_message(
                embed=discord.Embed(
                    color=discord.Color.grey(),
                    description='You are not eligible for Priority Roll as you have won with a priority bid previously.'
                ),
                ephemeral=True
            )
        else:
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

    async def display_winners_dropdown(self, interaction: Interaction, winners: list):
        options = [discord.SelectOption(label=winner) for winner in winners]
        self.winners_dropdown = discord.ui.SelectMenu(custom_id='winner_dropdown', placeholder='Select a winner', options=options)
        await interaction.response.send_message('Bidding period is over. Select a winner:', view=self.winners_dropdown)

class RandomBidSession:
    def __init__(self):
        self.results = {}
        self.auction_ids = {}
        self.previous_priority_winners = {}

    def add_auction(self, item_name):
        auction_id = str(uuid.uuid4())
        self.auction_ids[auction_id] = item_name
        return auction_id

    def add_result(self, auction_id, results):
        self.results[auction_id] = results

    def add_winner(self, auction_id, winner, bid_type):
        if bid_type == 'PRIORITY':
            self.previous_priority_winners[winner] = auction_id

        if auction_id in self.results:
            self.results[auction_id].append((winner, bid_type))
        else:
            self.results[auction_id] = [(winner, bid_type)]

    def get_results(self, auction_id):
        return self.results.get(auction_id)

    def get_summary(self):
        summary = {}
        total_items = 0
        total_unique_winners = set()

        for auction_id, auction_item in self.auction_ids.items():
            results = self.results.get(auction_id)
            if results:
                summary[auction_item] = [f"{winner[0]} ({winner[1]})" for winner in results]
                total_items += 1
                for winner in results:
                    total_unique_winners.add(winner[0])

        return summary, total_items, len(total_unique_winners)

random_bid_session = None

class CustomBot(discord.Client):
    min_bid = 1

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
        self.tree.add_command(get_results)
        self.tree.add_command(start_session)
        self.tree.add_command(end_session)
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user}')

bot = CustomBot()

@bot.tree.command(name='random')
@app_commands.guild_only()
@app_commands.describe(item='The name of the item', classes='Who can roll on the item', time='The time in seconds until the end of the bid')
async def start_random(interaction: Interaction, item: str, classes: str, time: Range[int, 1, 600]):
    global random_bid_session

    if random_bid_session is None:
        await interaction.response.send_message("There is no active session. Please start a session using /start_session command.", ephemeral=True)
        return

    auction_id = random_bid_session.add_auction(item)
    previous_priority_winners = random_bid_session.previous_priority_winners.values()
    view = RandomBidView(time, interaction.user.id, auction_id, previous_priority_winners)
    embed = discord.Embed(
        color=discord.Color.blue(),
        description=f'Now rolling: **{item}**!\n\nThe following may bid:\n**{classes}**'
    )

    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(time)
    view.stop()

    winners = [f'{interaction.guild.get_member(user_id).display_name} ({bid_type})' for user_id, bid_type in view.user_bids.items() if interaction.guild.get_member(user_id)]
    await view.display_winners_dropdown(interaction, winners)

@bot.event
async def on_select_menu(interaction: Interaction):
    if interaction.data.custom_id == 'winner_dropdown':
        auction_id = interaction.message.id
        winner = interaction.data.values[0]
        await interaction.response.defer_update()
        random_bid_session.add_winner(auction_id, winner.split(' ')[0], winner.split(' ')[1])

@bot.tree.command(name='get_results')
@app_commands.guild_only()
@app_commands.describe(item='The name of the item to get results for')
async def get_results(interaction: Interaction, item: str):
    if random_bid_session is None:
        await interaction.response.send_message("There is no active session. Please start a session using /start_session command.", ephemeral=True)
        return

    for auction_id, auction_item in random_bid_session.auction_ids.items():
        if item.lower() == auction_item.lower():
            results = random_bid_session.get_results(auction_id)
            if results:
                embed = discord.Embed(color=discord.Color.blue(), description='\n'.join(f'{winner[0]} ({winner[1]})' for winner in results))
                await interaction.response.send_message(embed=embed)
                return

    await interaction.response.send_message("No results found for that item.")

@bot.tree.command(name='start_session')
@app_commands.guild_only()
async def start_session(interaction: Interaction):
    global random_bid_session
    random_bid_session = RandomBidSession()
    await interaction.response.send_message("A new session has been started.", ephemeral=True)

@bot.tree.command(name='end_session')
@app_commands.guild_only()
async def end_session(interaction: Interaction):
    global random_bid_session
    if random_bid_session is None:
        await interaction.response.send_message("There is no active session.", ephemeral=True)
        return

    summary, total_items, total_unique_winners = random_bid_session.get_summary()

    if total_items == 0:
        await interaction.response.send_message("No items were auctioned in the current session.", ephemeral=True)
        return

    summary_message = "\n".join([f"**{item[0]}**: {', '.join(item[1])}" for item in summary])
    end_session_message = f"Summary of auction results:\n\n{summary_message}\n\nTotal items auctioned: {total_items}\nTotal unique winners: {total_unique_winners}"
    
    random_bid_session = None
    await interaction.response.send_message(end_session_message, ephemeral=True)

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

    if len(sorted_bids) >= 2:
        payment_amount = sorted_bids[1][1] + 1
    elif len(sorted_bids) == 1:
        payment_amount = bot.min_bid + 1
    else:
        payment_amount = None  

    winners_text = '\n'.join(f'{user} ({count}) bid {amount:,}' for user, amount, count in sorted_bids)
    payment_text = f"Payment amount: {payment_amount:,}" if payment_amount is not None else "No bids were placed!"

    embed.description += f'\n\n**Results**:\n{winners_text}\n\n{payment_text}'

    for item in view.children:
        item.disabled = True

    await interaction.edit_original_response(embed=embed, view=view)

@bot.tree.command(name='minbid')
@app_commands.describe(min_bid='The minimum bid amount')
async def set_min_bid(interaction: Interaction, min_bid: int):
    CustomBot.min_bid = max(1, min_bid)
    await interaction.response.send_message(f"Minimum bid set to {CustomBot.min_bid}.", ephemeral=True)

bot.run(config.TOKEN)
