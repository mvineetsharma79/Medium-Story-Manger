Create a new re-usable HTML (with seperate JS) component to place above Srories Table
# Requirment 
1. HTML and JS to show presentations, viewers, readers, netFollowersGained, netSubscribersGained and line chart to show points.stats.viewers and points.stats.readers for each day (timestamp)as time stamp for selected month on story screen.
2. Create and endpoint story-stats/ and story-stats/{period} in stories.py like @router.post("/refresh-stats/{period}") and @router.post("/refresh-stats/{period}") 
3. Create fetch_monthly_stats like fetch_medium_stats
4. Create fetch_medium_monthly_stats in medium_api_service.py like fetch_medium_stat using the Graph Query below and refrence response.
5. No data WILL be saved anywhere

# Task
1. Use Bootstrap's charts or suggest minimal with hover
2. Show the mapping with proposed HTML/Chart
3. How you'll make it to 


# Grapg Query
```
[{"operationName":"UserMonthlyStoryStatsTimeseriesQuery","variables":{"username":"mvineetsharma","input":{"startTime":1777593600000,"endTime":1778630400000}},"query":"query UserMonthlyStoryStatsTimeseriesQuery($username: ID!, $input: UserPostsAggregateStatsInput!) {\n  user(username: $username) {\n    id\n    postsAggregateTimeseriesStats(input: $input) {\n      __typename\n      ... on AggregatePostTimeseriesStats {\n        ...MonthlyStoryStats_aggregatePostTimeseriesStats\n        __typename\n      }\n    }\n    __typename\n  }\n}\n\nfragment MonthlyStoryStatsTotals_postStats on PostStats {\n  presentations\n  viewers\n  readers\n  netFollowersGained\n  netSubscribersGained\n  __typename\n}\n\nfragment MonthlyStoryStatsChart_postStatsPoint on PostStatsPoint {\n  timestamp\n  stats {\n    total {\n      viewers\n      readers\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment MonthlyStoryStats_aggregatePostTimeseriesStats on AggregatePostTimeseriesStats {\n  totalStats {\n    ...MonthlyStoryStatsTotals_postStats\n    __typename\n  }\n  points {\n    ...MonthlyStoryStatsChart_postStatsPoint\n    __typename\n  }\n  __typename\n}\n"}]
```
# Response
```
[
    {
        "data": {
            "user": {
                "id": "6a63927f9b83",
                "postsAggregateTimeseriesStats": {
                    "__typename": "AggregatePostTimeseriesStats",
                    "totalStats": {
                        "presentations": 14990,
                        "viewers": 4412,
                        "readers": 1068,
                        "netFollowersGained": 30,
                        "netSubscribersGained": 24,
                        "__typename": "PostStats"
                    },
                    "points": [
                        {
                            "timestamp": 1777593600000,
                            "stats": {
                                "total": {
                                    "viewers": 432,
                                    "readers": 75,
                                    "__typename": "PostStats"
                                },
                                "__typename": "PostStatsBreakdown"
                            },
                            "__typename": "PostStatsPoint"
                        },
                        {
                            "timestamp": 1777680000000,
                            "stats": {
                                "total": {
                                    "viewers": 431,
                                    "readers": 85,
                                    "__typename": "PostStats"
                                },
                                "__typename": "PostStatsBreakdown"
                            },
                            "__typename": "PostStatsPoint"
                        }
                    ]
                },
                "__typename": "User"
            }
        }
    }
]
```