#!/usr/bin/env python3.6
# encoding: utf-8

import logging
import typing

import discord
from discord.ext import commands

from reactor_bot import emoji_utils

logger = logging.getLogger('cogs.db')

class Database(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	async def set_poll_emoji(self, channel: int, yes, no, shrug):
		# ok so sometimes the shitty discord client doesn't send us actual emojis, but shortcodes
		# which we cannot react with…
		# so we have to convert them from shortcodes to unicode.
		yes, no, shrug = map(emoji_utils.convert_shortcode, (yes, no, shrug))
		# mfw no INSERT OR REPLACE in postgres
		await self.bot.pool.execute("""
			INSERT INTO poll_emoji (channel, yes, no, shrug)
			VALUES ($1, $2, $3, $4)
			ON CONFLICT (channel)
			DO UPDATE SET
				yes   = EXCLUDED.yes,
				no    = EXCLUDED.no,
				shrug = EXCLUDED.shrug
		""", channel, yes, no, shrug)

	async def get_poll_emoji(self, channel: int):
		return await self.bot.pool.fetchrow("""
			SELECT yes, no, shrug
			FROM poll_emoji
			WHERE channel = $1
		""", channel)

	@commands.command(name='set-emoji', aliases=['set-poll-emoji'])
	async def set_poll_emoji_command(self, context, channel: typing.Optional[discord.TextChannel], yes, no, shrug):
		"""Sets the poll emoji for channel (or the current one) to the emojis provided.

		- All three arguments must be emojis. If an invalid emoji is provided, that reaction will be disabled.
		- You must have the Manage Channels permission on the provided channel to use this command.
		"""
		channel = channel or context.channel
		if not channel.permissions_for(context.author).manage_channels:
			raise commands.MissingPermissions(('manage_channels',))
		await self.set_poll_emoji(channel.id, yes, no, shrug)
		await context.message.add_reaction(self.bot.config['success_or_failure_emojis']["True"])

	async def set_prefixless_channel(self, channel: int):
		statement = """
			INSERT INTO prefixless_channels
			VALUES ($1)
			ON CONFLICT DO NOTHING;"""
		await self.bot.pool.execute(statement, channel)

	async def unset_prefixless_channel(self, channel: int):
		await self.bot.pool.execute('DELETE FROM prefixless_channels WHERE channel = $1', channel)

	async def is_prefixless_channel(self, channel: int):
		result = await self.bot.pool.fetchval('SELECT 1 FROM prefixless_channels WHERE channel = $1', channel)
		return bool(result)

	@commands.command()
	async def prefixless(self, context, channel: typing.Optional[discord.TextChannel], prefixless: bool):
		"""Sets a channel up to be "prefix-less".

		All messages sent in that channel will be treated as a poll.
		You must have the "Manage Channels" permission on the provided channel to use this command.
		"""
		channel = channel or context.channel
		if not channel.permissions_for(context.author).manage_channels:
			raise commands.MissingPermissions(('manage_channels',))
		func = self.set_prefixless_channel if prefixless else self.unset_prefixless_channel
		await func(channel.id)
		await context.message.add_reaction(self.bot.config['success_or_failure_emojis']["True"])


def setup(bot):
	bot.add_cog(Database(bot))
