# Tram22Bot

Tram22Bot is a Discord/Telegram/Twitter bot written in Python for informing the user of any calamities related to U-OV's tram line 22.

To see the bot in action, [visit its Twitter account](https://twitter.com/Tram22RijdtNiet).

## Usage

To set up the bot, you are only required to run the tram22.py script. It automatically generates all required jsons, and furthermore generates a file called '.env', which saves your Discord token, for which you are prompted.

## File tree

Your project should look as follows,

```
|   .gitignore
│   LICENSE
│   README.md
│
├───env
│       .env
│
├───json
│       discorddata.json
│       discordguilddata.json
│       telegramdata.json
│       tram22.json
│
├───src
│       tram22.py
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)
