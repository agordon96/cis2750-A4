Aaron Gordon 0884023
CIS*2750 Assignment 4

Grade Breakdown:
- Correct tables and database connection, command line arguments complete
- Usability of UI additions mostly done, barely any error handling
- Store All Events functions completely and stores all events properly
- Store Current Event gets selected event, stores properly
- Clear All Data is completely functional and is disabled if tables are empty
- Display DB Status is completely functional and always active
- Execute Query has full functionality (but looks kinda gross)

My computer was an hour behind for whatever reason. I know that won't mean much and it'll probably still get the -3% but it kind of slipped my mind as I was working on it and didn't notice until I saw the red on submission.

NOTE FOR EXECUTE QUERY:

First two are straightforward. For locations, I decided on Coruscant which only has one organizer in my file (General Kenobi) where the other two events have NULL and Naboo as their locations. For contact, I showed email using a simple SELECT, but I also added a join in a second query to check if there's a location for a particular event they're going to and telling you when they'll be there (like General Kenobi going to Coruscant). For alarms, I did a condition for when there are alarms present then the data is displayed, and nothing if there are no alarms present.