1. Rename "Update Leaderbaoard Stories" to "Update Leaderbaoard"
2. Create new button "Fetch Leaderbaoard"
3. Read the leadeboard-xxxx-xx.json (like "leaderboard-2026-04.josn" xxxx-xx as year 2026 and month 04) from /data/leadeboard-xxxx-xx.json

Scan thru data.userResult.postsConnection.edges from JSON
5. Reset "Leaderboard" flag to false for all stories
4. Check if story exist (node.title)
If story not exists 
    a. Create new Story in "Leaderboard" Series
    b. Follow the update workflow as "Update" 
if story exists 
	a. Update the Publish date from node.firstPublishedAt and change status to "Publish"
	b. Update medium_reading_time = node.readingTime, 
	c. Update medium_publication = node.collection.slug
	d. Update medium_url = node.mediumUrl
	e. Set Leaderboard to true
	f. Update leaderboard_nanos as node.earnings.monthlyEarnings.nanos
	g. Update leaderboard_lifetime_nanos (new field) as node.earnings.lifetimeEarnings.nanos