# LVS-F1-Fantasy-Discord-Bot
A modular, open source Discord bot which can be used to maintain a Formula 1 Fantasy League on a Discord server.

# Goals

## Modular Setup
Should be able to start and maintian multiple leagues in the same guild, as well as be added to several guilds.

## Flexible Rulesets
League administrators should be able to modify existing rulesets, as well as create new rules with relative ease. The bot should be flexible enough to sustain fantasy leagues for many years.

## Database Driven
All data pertaining to the league including data about players, drivers, constructors, Grand Prix events, etc. should be stored in an all encompassing database, with an easy-to-navigate database schema.

## On-The-Fly Adaptability
The Formula One season can sometimes be unpredictable and many changes can take place such as Grand Prixs being cancelled or rescheduled, drivers being replaced or removed during the season, etc. The bot should interact with the database in a decoupled manner, so that players, drivers, events, etc. can be added and removed during the season without any modification to bot methods.

# Proposed Features

## Player Features

### Register
Allow players to register and de-register themselves to the league.

**Admin Parameters** - Optional registration period, with a start date and end date.

### Draft
Allow players to draft drivers into their teams, within a certain time period defined in the rules.

**Admin Parameters** - Define when draft window is open/closed.

### View Team
Allow players to view their team at any given point. If a team has not been drafted for the current round, the previous round's team will be displayed.

**Optional Parameters**
- user - View the team of another user, if within the accepted time window.

### Check Exhausted Drivers
Allow players to check the list of drivers they have exhausted, if any.

### Display Leaderboard
Allow players to view the league leaderboard as it currently stands, with the option of viewing the leaderboards of previous years.

### Display Points Table
Allow players to view a detailed points table, showing the points scored by every player at every Grand Prix weekend.

### Display Season Statistics
Allow players to view detailed information about any Grand Prix event, driver, constructor or other player.

#### List of Season Statistics
- **Grand Prix Weekends**
    - Results for all sessions
    - Session dates and times in local timezone
    - Full Grand Prix event names

- **Drivers**
    - Constructor
    - Race wins
    - Highest finishing position
    - Lowest finishing position
    - Podiums
    - Teammate Battle (Race)
    - Teammate Battle (Qualifying)
    - Drivers' Championship position
    - Drivers' Championship points
    - Last race result
    - Last qualifying result
    - Positions gained
    - Positions Lost

- **Constructors**
    - 2 Drivers
    - Reserve Driver
    - Constructors' Championship position
    - Constructors' Championship points
    - Drivers' Championship points for each driver
    - Drivers' teammate battle (Race)
    - Drivers' teammate battle (Qualifying)
    - Headquarters location
    - Team Principal
    - CEO
    - Engine supplier

- **Players**
    - Fantasy League Points
    - Fantasy League Leaderboard position
    - Most picked driver
    - Most picked constructor
    - League wins
    - Average points per race
    - Graph of race results over the season

### Compare Performance
Allow players to compare their season-wide statistics against each other.

## Admin Features

### Start League
Allow admins to create a new league

### Assign Random Teams
Allow admins to assign random teams to players who have not drafted their teams for the weekend.

### Update Weekend Points
Allow admins to update points and standings for each race weekend.

### Assign Team to Player
Allow admins to assign a team to any player

### View Player Teams
Allow admins to view the teams of any players at any time.

### Archive League
Allow admins to create an archived version of the current league

### Schedule Guild Events
Allow admins to populate guild events with the Formula 1 Calendar.

### Bot Message Interactions
Allow admins to control the bot user and send messages, reply and react, etc.
