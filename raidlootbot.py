import asyncio
import random
import discord
from discord import app_commands, Interaction
from discord.app_commands import Range
import config

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
        await self.handle_bid(interaction, "Priority Roll")

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

class CustomSelect(discord.ui.Select):
    def __init__(self, placeholder, options, message=None):
        super().__init__(placeholder=placeholder, options=options, custom_id='custom_select_menu')
        self.message = message

    async def callback(self, interaction: discord.Interaction):
        try:
            selected_option_value = self.values[0]
            selected_option = [option for option in self.options if option.value == selected_option_value][0]
            selected_user = selected_option.label
            print(f"User is : {selected_user}")
        except Exception as e:
            print(f"An error occurred: {e}")



class RandomParticipantsList:
    def __init__(self):
        self.participants = {}  

    def add_participant(self, item_name: str, participant: str):
        if item_name not in self.participants:
            self.participants[item_name] = []  
        self.participants[item_name].append(participant)

    def get_participants(self, item_name: str):
        return self.participants.get(item_name, [])

    def clear_participants(self, item_name: str):
        if item_name in self.participants:
            del self.participants[item_name]
    async def on_ready(self):
        print(f'Logged in as {self.user}')

class CustomBot(discord.Client):
    min_bid = 1

    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents, help_command=None)
        self.tree = app_commands.CommandTree(self)
        self.random_participants_list = RandomParticipantsList()

    async def setup_hook(self):
        self.tree.clear_commands(guild=None)
        self.tree.add_command(start_random)
        self.tree.add_command(start_bids)
        self.tree.add_command(set_min_bid)
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        for guild in self.guilds:
            print(f"Bot permissions in {guild.name}: {guild.me.guild_permissions}")

    async def on_interaction(self, interaction: discord.Interaction):
        print(f"Received interaction: {interaction}")
        print(f"Interaction type: {interaction.type}")
        print(f"Interaction data: {interaction.data}")

        # Check if the interaction is a select menu interaction
        if interaction.type == discord.InteractionType.component:
            print("Interaction is a component interaction.")
            print(f"Component type: {interaction.data.get('component_type')}")

            if interaction.data.get("custom_id") == "custom_select_menu":
                # Handle select menu interaction
                print("Handling select menu interaction...")
                await self.handle_select_menu(interaction)
            else:
                # Interaction doesn't meet the criteria, skip processing
                print("Interaction does not have the expected custom ID. Skipping...")
        else:
            # Interaction is not a component interaction
            print("Interaction is not a component interaction. Skipping...")

        print("Interaction processing completed.")


        print("Interaction processing completed.")

    async def handle_select_menu(self, interaction: discord.Interaction):
        # Extract selected option from interaction
        selected_option_value = interaction.data["values"][0]

        # Process selected option
        print(f"Selected option: {selected_option_value}")
        await interaction.response.send_message(f"You selected option: {selected_option_value}")




bot = CustomBot()

@bot.tree.command(name='random')
@app_commands.guild_only()
@app_commands.describe(item='The name of the item', classes='Who can roll on the item', time='The time in seconds until the end of the bid')
async def start_random(interaction: Interaction, item: str, classes: str, time: Range[int, 1, 600]):
    if interaction is None:
        # Handle the case where interaction is None
        return

    view = RandomBidView(time)
    embed = discord.Embed(
        color=discord.Color.blue(),
        description=f'Now rolling: **{item}**!\n\nThe following may bid:\n**{classes}**'
    )

    await interaction.response.send_message(embed=embed, view=view)

    await asyncio.sleep(time)
    view.stop()

    priority_rolls = [f'{interaction.guild.get_member(user_id).display_name} ({bid_type})' for user_id, bid_type in view.user_bids.items() if interaction.guild.get_member(user_id) and bid_type == 'Priority Roll']
    standard_rolls = [f'{interaction.guild.get_member(user_id).display_name} ({bid_type})' for user_id, bid_type in view.user_bids.items() if interaction.guild.get_member(user_id) and bid_type == 'Standard Roll']

    random.shuffle(priority_rolls)
    random.shuffle(standard_rolls)

    sorted_bids = priority_rolls + standard_rolls

    participants_text = '\n'.join(sorted_bids) if sorted_bids else "No users joined!"
    embed.description += f'\n\n**Results**:\n{participants_text}'

    for button in view.children:
        button.disabled = True

    await interaction.edit_original_response(embed=embed, view=view)

    select_options = [discord.SelectOption(label=participant, value=str(i)) for i, participant in enumerate(sorted_bids)]
    select = CustomSelect(placeholder="Select a participant", options=select_options)
    select_view = discord.ui.View()
    select_view.add_item(select)

    select_message = await interaction.followup.send(content=f"Participants for {item}:", view=select_view, ephemeral=True)
    select = CustomSelect(placeholder="Select a participant", options=select_options, message=select_message)





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

    participants_text = '\n'.join(f'{user} bid {amount:,}' for user, amount in sorted_bids)
    payment_text = f"Payment amount: {payment_amount:,}" if payment_amount is not None else "No bids were placed!"

    embed.description += f'\n\n**Results**:\n{participants_text}\n\n{payment_text}'

    for item in view.children:
        item.disabled = True

    await interaction.edit_original_response(embed=embed, view=view)

@bot.tree.command(name='minbid')
@app_commands.describe(min_bid='The minimum bid amount')
async def set_min_bid(interaction: Interaction, min_bid: int):
    """Sets the minimum bid amount."""
    CustomBot.min_bid = max(1, min_bid)
    await interaction.response.send_message(f"Minimum bid set to {CustomBot.min_bid}.", ephemeral=True)

bot.run(config.TOKEN)
