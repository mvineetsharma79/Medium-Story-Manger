"""
Stories Router - Complete endpoints with uniqueSlug as primary key
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from urllib.parse import unquote
import re
import json
from pathlib import Path
from app.services.file_service import load_stories_data

from app.services.story_service import StoryService
from app.services.monthly_storage_service import MonthlyStorageService
from app.services.medium_api_service import get_medium_api_service
from app.services.app_status_service import AppStatusService
from app.models import StoryCreate, StoryUpdate, StoryResponse
from app.utils import (
    find_story_by_identifier,
    normalize_title,
    normalize_url,
    extract_post_id_from_url,
    calculate_percentages,
    get_current_year_month
)

from app.services.file_service import (
    load_stories_data, save_stories_data, scan_markdown_files,
    parse_series_number
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


"""
POST /api/stories/refresh-stats
Description: Refresh stats from Medium API for current month

curl -X POST "http://localhost:8000/api/stories/refresh-stats" | jq '.'
"""
@router.post("/refresh-stats")
async def refresh_stats_current_month():
    """Refresh stats from Medium API for current month"""
    try:
        year, month = get_current_year_month()
        return await refresh_stats_with_period(f"{year}-{month}")
    except Exception as e:
        logger.error(f"Error refreshing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


"""
POST /api/stories/refresh-stats/{period}
Description: Refresh stats from Medium API for specific period (YYYY-MM)

curl -X POST "http://localhost:8000/api/stories/refresh-stats/2026-04" | jq '.'
"""
#             timeRange: {startAt: $startAt, endAt: $endAt} - removed
queryEarning = """
query StoryEarningsQuery(
  $username: ID!
  $first: Int!
  $after: String!
  $startAt: Long!
  $endAt: Long!
) {
  userResult(username: $username) {
    ... on User {
      id
      username
      name
      postsConnection(
        first: $first
        after: $after
        orderBy: { lifetimeEarnings: DESC }
        filter: { published: true }
      ) {
        edges {
          node {
            id
            title
            uniqueSlug
            mediumUrl
            createdAt
            updatedAt
            firstPublishedAt
            firstBoostedAt
            readingTime
            wordCount
            clapCount
            responsesCount
            voterCount
            isLocked
            visibility
            isSeries
            isShortform
            license
            
            totalStats {
              presentations
              views
              reads
              __typename
            }
            
            dailyStats(startAt: $startAt, endAt: $endAt) {
              views
              
              __typename
            }
            
            tags {
              id
            }
            
            earnings {
              total {
                currencyCode
                units
                nanos
                __typename
              }
              monthlyEarnings: total(input: { between: { startAt: $startAt, endAt: $endAt } }) {
                currencyCode
                units
                nanos
                __typename
              }
              __typename
            }
            
            creator {
              id
              username
              name
              bio
              imageId
              twitterScreenName
              createdAt
            }
            
            collection {
              id
              name
              slug
              domain
              subscriberCount
              createdAt
            }
            
            __typename
          }
          cursor
        }
        pageInfo {
          endCursor
          hasNextPage
        }
      }
    }
  }
}"""

queryStories= """
query UserLifetimeStoryStatsPostsQuery(
  $username: ID!
  $first: Int!
  $after: String!
  $orderBy: UserPostsOrderBy
  $filter: UserPostsFilter
  $startAt: Long!
  $endAt: Long!
) {
  user(username: $username) {
    id
    postsConnection(
      first: $first
      after: $after
      orderBy: $orderBy
      filter: $filter
    ) {
      __typename
      edges {
        ...UserLifetimeStoryStats_relayPostEdge
        __typename
      }
      pageInfo {
        endCursor
        hasNextPage
        __typename
      }
    }
    __typename
  }
}

fragment UserLifetimeStoryStats_relayPostEdge on RelayPostEdge {
  node {
    id
    ...LifetimeStoryStats_post
    __typename
  }
  __typename
}

fragment LifetimeStoryStats_post on Post {
  id
  ...StoryStatsTable_post
  __typename
}

fragment StoryStatsTable_post on Post {
  ...StoryStatsTableRow_post
  __typename
  id
}

fragment StoryStatsTableRow_post on Post {
  id
  isLocked
  totalStats {
    presentations
    views
    reads
    __typename
  }
  dailyStats(startAt: $startAt, endAt: $endAt) {
    views
    __typename
  }
  tags {
    id
  }
  earnings {
    total {
      currencyCode
      nanos
      units
      __typename
    }
    monthlyEarnings: total(input: { between: { startAt: $startAt, endAt: $endAt } }) {
      currencyCode
      units
      nanos
      __typename
    }
    __typename
  }
  ...TablePostInfos_post
  ...usePostStatsUrl_post
  ...shouldDisplayFeaturedIcon_post
  __typename
}

fragment TablePostInfos_post on Post {
  id
  title
  readingTime
  isLocked
  visibility
  createdAt
  updatedAt
  firstPublishedAt
  firstBoostedAt
  wordCount
  clapCount
  responsesCount
  voterCount
  isSeries
  isShortform
  license
  uniqueSlug
  mediumUrl
  ...usePostUrl_post
  ...Star_post
  ...PostPreviewByLine_post
  __typename
}

fragment usePostUrl_post on Post {
  id
  creator {
    ...userUrl_user
    __typename
    id
  }
  collection {
    id
    domain
    slug
    __typename
  }
  isSeries
  mediumUrl
  sequence {
    slug
    __typename
  }
  uniqueSlug
  __typename
}

fragment userUrl_user on User {
  __typename
  id
  customDomainState {
    live {
      domain
      __typename
    }
    __typename
  }
  hasSubdomain
  username
}

fragment Star_post on Post {
  id
  __typename
}

fragment PostPreviewByLine_post on Post {
  creator {
    ...PostPreviewByLineAuthor_user
    __typename
    id
  }
  collection {
    ...PostPreviewByLineCollection_collection
    __typename
    id
  }
  __typename
  id
}

fragment PostPreviewByLineAuthor_user on User {
  ...PostPreviewBylineAuthorAvatar_user
  ...UserName_user
  __typename
  id
}

fragment PostPreviewBylineAuthorAvatar_user on User {
  ...UserAvatar_user
  __typename
  id
}

fragment UserAvatar_user on User {
  __typename
  id
  imageId
  membership {
    tier
    __typename
    id
  }
  name
  username
  ...userUrl_user
}

fragment UserName_user on User {
  id
  name
  ...isUserVerifiedBookAuthor_user
  ...UserLink_user
  __typename
}

fragment isUserVerifiedBookAuthor_user on User {
  verifications {
    isBookAuthor
    __typename
  }
  __typename
  id
}

fragment UserLink_user on User {
  ...userUrl_user
  __typename
  id
}

fragment PostPreviewByLineCollection_collection on Collection {
  ...CollectionAvatar_collection
  ...CollectionTooltip_collection
  ...CollectionLinkWithPopover_collection
  __typename
  id
}

fragment CollectionAvatar_collection on Collection {
  name
  avatar {
    id
    __typename
  }
  ...collectionUrl_collection
  __typename
  id
}

fragment collectionUrl_collection on Collection {
  id
  domain
  slug
  __typename
}

fragment CollectionTooltip_collection on Collection {
  id
  name
  slug
  description
  subscriberCount
  customStyleSheet {
    header {
      backgroundImage {
        id
        __typename
      }
      __typename
    }
    __typename
    id
  }
  ...CollectionAvatar_collection
  ...PublicationFollowButton_collection
  ...EntityPresentationRankedModulePublishingTracker_entity
  __typename
}

fragment PublicationFollowButton_collection on Collection {
  id
  slug
  name
  ...SusiModal_collection
  __typename
}

fragment SusiModal_collection on Collection {
  name
  ...SignInOptions_collection
  ...SignUpOptions_collection
  __typename
  id
}

fragment SignInOptions_collection on Collection {
  id
  name
  __typename
}

fragment SignUpOptions_collection on Collection {
  id
  name
  __typename
}

fragment EntityPresentationRankedModulePublishingTracker_entity on RankedModulePublishingEntity {
  __typename
  ... on Collection {
    id
    __typename
  }
  ... on User {
    id
    __typename
  }
}

fragment CollectionLinkWithPopover_collection on Collection {
  name
  ...collectionUrl_collection
  ...CollectionTooltip_collection
  __typename
  id
}

fragment usePostStatsUrl_post on Post {
  id
  creator {
    id
    username
    __typename
  }
  __typename
}

fragment shouldDisplayFeaturedIcon_post on Post {
  id
  isFeaturedInPublishedPublication
  collection {
    id
    __typename
  }
  __typename
}
"""

queryUserMonthlyStoryStatsTimeseriesQuery = """
query UserLifetimeStoryStatsPostsQuery(
  $username: ID!
  $first: Int!
  $after: String!
  $orderBy: UserPostsOrderBy
  $filter: UserPostsFilter
  $startAt: Long!
  $endAt: Long!
  $aggregateInput: UserPostsAggregateStatsInput!
) {
  user(username: $username) {
    id
    
    # Posts connection with per-post stats
    postsConnection(
      first: $first
      after: $after
      orderBy: $orderBy
      filter: $filter
    ) {
      __typename
      edges {
        node {
          id
          ...StoryStatsTableRow_post
          __typename
        }
        __typename
      }
      pageInfo {
        endCursor
        hasNextPage
        __typename
      }
    }
    
    # Aggregate stats across ALL posts
    postsAggregateTimeseriesStats(input: $aggregateInput) {
      
      __typename
      ... on AggregatePostTimeseriesStats {
        totalStats {
          presentations
          viewers
          readers
          netFollowersGained
          netSubscribersGained
          __typename
        }
        points {
            
          timestamp
          stats {
            total {
              viewers
              readers
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
    }
    
    __typename
  }
}

fragment StoryStatsTableRow_post on Post {
  id
  isLocked
  totalStats {
    presentations
    views
    reads
    __typename
  }
  
  # Daily views - uses $startAt and $endAt
  dailyStats(startAt: $startAt, endAt: $endAt) {
    views
    __typename
  }
  
  # Daily earnings
  earnings {
    dailyEarnings(startAt: $startAt, endAt: $endAt) {
      periodStartedAt
      amount
      __typename
    }
    total {
      currencyCode
      nanos
      units
      __typename
    }
    monthlyEarnings: total(input: { between: { startAt: $startAt, endAt: $endAt } }) {
      currencyCode
      units
      nanos
      __typename
    }
    __typename
  }
  
  tags {
    id
  }
  ...TablePostInfos_post
  ...usePostStatsUrl_post
  ...shouldDisplayFeaturedIcon_post
  __typename
}

fragment TablePostInfos_post on Post {
  id
  title
  readingTime
  isLocked
  visibility
  createdAt
  updatedAt
  firstPublishedAt
  firstBoostedAt
  wordCount
  clapCount
  responsesCount
  voterCount
  isSeries
  isShortform
  license
  uniqueSlug
  mediumUrl
  ...usePostUrl_post
  ...Star_post
  ...PostPreviewByLine_post
  __typename
}

fragment usePostUrl_post on Post {
  id
  creator {
    ...userUrl_user
    __typename
    id
  }
  collection {
    id
    domain
    slug
    __typename
  }
  isSeries
  mediumUrl
  sequence {
    slug
    __typename
  }
  uniqueSlug
  __typename
}

fragment userUrl_user on User {
  __typename
  id
  customDomainState {
    live {
      domain
      __typename
    }
    __typename
  }
  hasSubdomain
  username
}

fragment Star_post on Post {
  id
  __typename
}

fragment PostPreviewByLine_post on Post {
  creator {
    ...PostPreviewByLineAuthor_user
    __typename
    id
  }
  collection {
    ...PostPreviewByLineCollection_collection
    __typename
    id
  }
  __typename
  id
}

fragment PostPreviewByLineAuthor_user on User {
  ...PostPreviewBylineAuthorAvatar_user
  ...UserName_user
  __typename
  id
}

fragment PostPreviewBylineAuthorAvatar_user on User {
  ...UserAvatar_user
  __typename
  id
}

fragment UserAvatar_user on User {
  __typename
  id
  imageId
  membership {
    tier
    __typename
    id
  }
  name
  username
  ...userUrl_user
}

fragment UserName_user on User {
  id
  name
  ...isUserVerifiedBookAuthor_user
  ...UserLink_user
  __typename
}

fragment isUserVerifiedBookAuthor_user on User {
  verifications {
    isBookAuthor
    __typename
  }
  __typename
  id
}

fragment UserLink_user on User {
  ...userUrl_user
  __typename
  id
}

fragment PostPreviewByLineCollection_collection on Collection {
  ...CollectionAvatar_collection
  ...CollectionTooltip_collection
  ...CollectionLinkWithPopover_collection
  __typename
  id
}

fragment CollectionAvatar_collection on Collection {
  name
  avatar {
    id
    __typename
  }
  ...collectionUrl_collection
  __typename
  id
}

fragment collectionUrl_collection on Collection {
  id
  domain
  slug
  __typename
}

fragment CollectionTooltip_collection on Collection {
  id
  name
  slug
  description
  subscriberCount
  customStyleSheet {
    header {
      backgroundImage {
        id
        __typename
      }
      __typename
    }
    __typename
    id
  }
  ...CollectionAvatar_collection
  ...PublicationFollowButton_collection
  ...EntityPresentationRankedModulePublishingTracker_entity
  __typename
}

fragment PublicationFollowButton_collection on Collection {
  id
  slug
  name
  ...SusiModal_collection
  __typename
}

fragment SusiModal_collection on Collection {
  name
  ...SignInOptions_collection
  ...SignUpOptions_collection
  __typename
  id
}

fragment SignInOptions_collection on Collection {
  id
  name
  __typename
}

fragment SignUpOptions_collection on Collection {
  id
  name
  __typename
}

fragment EntityPresentationRankedModulePublishingTracker_entity on RankedModulePublishingEntity {
  __typename
  ... on Collection {
    id
    __typename
  }
  ... on User {
    id
    __typename
  }
}

fragment CollectionLinkWithPopover_collection on Collection {
  name
  ...collectionUrl_collection
  ...CollectionTooltip_collection
  __typename
  id
}

fragment usePostStatsUrl_post on Post {
  id
  creator {
    id
    username
    __typename
  }
  __typename
}

fragment shouldDisplayFeaturedIcon_post on Post {
  id
  isFeaturedInPublishedPublication
  collection {
    id
    __typename
  }
  __typename
}
"""



@router.post("/refresh-stats/{period}")
async def refresh_stats_with_period(period: str):
    try:
        datetime.strptime(period, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid period format")
    
    ## Get ALl Stoies from JSON
    data = await load_stories_data()
    stories = data.get("stories", {})
    series_data = data.get("series", {})
    
    if "Medium" not in series_data:
        series_data["Medium"] = {
            "name": "Medium",
            "total_stories": 0,
            "published": 0,
            "spacing_days": 7,
            "stories": []
        }
    
    
    ## Get ALl Stoies from API
    api_service = get_medium_api_service()    
    if not api_service.is_authenticated():
        return {
            "success": False,
            "message": "Not authenticated. Please login to Medium.",
            "period": period,
            "new_stories": 0,
            "updated_stories": 0,
            "total_posts": 0
        }
    parts = period.split('-')
    year = 2026 #int(parts[0])
    month = 3 #int(parts[1])
    start_at, end_at = api_service.get_month_timestamps(year, month)
    username = 'mvineetsharma'

    # variables = {
    #     "username": username,
    #     "first": 1,
    #     "after": "",
    #     "startAt": start_at,
    #     "endAt": end_at
    # }
    variables = {
        "username": username,
        "first": 1,
        "after": "",    
        "startAt": start_at,
        "endAt": end_at,
            "filter": {
            "published": True
        },
        "orderBy": {
            "lifetimeEarnings": "DESC"
        }
        
            
    }
    
    
    
    operation = "StoryEarningsQuery"
    query = queryEarning        
    
    #operation = "UserLifetimeStoryStatsPostsQuery"
    #query = queryStories
    payload = api_service._build_graphql_request(operation, variables, query, username, "stats-post")
    headers = api_service._get_common_headers(username, operation)
    
    
    posts = api_service._make_request(api_service.GRAPHQL_URL, headers, payload, f"Fetch Medium Stories {period}")

    if not posts:
        logger.warning(f"No response from Medium API for {period}")
        return None
    process_reponse = []
    response_item = posts[0]
    pageInfo = response_item['data']['userResult']['postsConnection']['pageInfo']
    
    data_obj = response_item['data']['userResult']['postsConnection']['edges']
    node_stories =[]
    # node_data = {
    #     'id' : '',
    #     'title':'',
    #  'mediumURL' :''   
    # }
    for node in data_obj:
        # data = node['title']
        node_data ={}
        node_data['id'] = node['node']['id']
        node_data['title'] = node['node']['title']
        node_data['period'] =   month
        node_data['earnings'] = node['node']['earnings']
        node_data['totalStats'] = node['node']['totalStats']
        node_stories.append(node_data)
        logger.warning(f"Post Title {node['node']['title']}")

    #     process_reponse.append(title) 
    
    # result = await StoryService.medium_query(period)
    return posts

# End Stats 


# UserLifetimeStoryStatsPostsQuery
# [
#   {
#     "data": {
#       "user": {
#         "id": "6a63927f9b83",
#         "postsConnection": {
#           "__typename": "RelayPostConnection",
#           "edges": [
#             {
#               "node": {
#                 "id": "40793d1e9f2b",
#                 "firstPublishedAt": 1746026444668,
#                 "isLocked": true,
#                 "totalStats": {
#                   "presentations": 7947,
#                   "views": 4033,
#                   "reads": 2167,
#                   "__typename": "SummaryPostStat"
#                 },
#                 "earnings": {
#                   "total": {
#                     "currencyCode": "USD",
#                     "nanos": 500000000,
#                     "units": 17,
#                     "__typename": "Money"
#                   },
#                   "__typename": "PostEarnings"
#                 },
#                 "title": "Achieving 10x Faster Serialization in .NET Core",
#                 "readingTime": 4.8437106918239,
#                 "visibility": "LOCKED",
#                 "firstBoostedAt": null,
#                 "creator": {
#                   "__typename": "User",
#                   "id": "6a63927f9b83",
#                   "customDomainState": {
#                     "live": {
#                       "domain": "mvineetsharma.medium.com",
#                       "__typename": "CustomDomain"
#                     },
#                     "__typename": "CustomDomainState"
#                   },
#                   "hasSubdomain": true,
#                   "username": "mvineetsharma",
#                   "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
#                   "membership": null,
#                   "name": "Vineet Sharma",
#                   "verifications": {
#                     "isBookAuthor": false,
#                     "__typename": "VerifiedInfo"
#                   }
#                 },
#                 "collection": null,
#                 "isSeries": false,
#                 "mediumUrl": "https://mvineetsharma.medium.com/achieving-10x-faster-serialization-in-net-core-40793d1e9f2b",
#                 "sequence": null,
#                 "uniqueSlug": "achieving-10x-faster-serialization-in-net-core-40793d1e9f2b",
#                 "__typename": "Post",
#                 "isFeaturedInPublishedPublication": false
#               },
#               "__typename": "RelayPostEdge"
#             }
#           ],
#           "pageInfo": {
#             "endCursor": "1",
#             "hasNextPage": true,
#             "__typename": "PageInfoV2"
#           }
#         },
#         "__typename": "User"
#       }
#     }
#   }
# ]

# StoryEarningsQuery response  
# [
#   {
#     "data": {
#       "userResult": {
#         "id": "6a63927f9b83",
#         "username": "mvineetsharma",
#         "name": "Vineet Sharma",
#         "postsConnection": {
#           "edges": [
#             {
#               "node": {
#                 "id": "40793d1e9f2b",
#                 "__typename": "Post",
#                 "title": "Achieving 10x Faster Serialization in .NET Core",
#                 "uniqueSlug": "achieving-10x-faster-serialization-in-net-core-40793d1e9f2b",
#                 "mediumUrl": "https://mvineetsharma.medium.com/achieving-10x-faster-serialization-in-net-core-40793d1e9f2b",
#                 "createdAt": 1746023966663,
#                 "updatedAt": 1776144717884,
#                 "firstPublishedAt": 1746026444668,
#                 "totalStats": {
#                   "presentations": 7947,
#                   "views": 4033,
#                   "reads": 2167,
#                   "__typename": "SummaryPostStat"
#                 },
#                 "readingTime": 4.8437106918239,
#                 "wordCount": 1182,
#                 "clapCount": 51,
#                 "responsesCount": 1,
#                 "voterCount": 31,
#                 "isLocked": true,
#                 "visibility": "LOCKED",
#                 "isSeries": false,
#                 "isShortform": false,
#                 "firstBoostedAt": null,
#                 "license": "ALL_RIGHTS_RESERVED",
#                 "tags": [
#                   {
#                     "id": "serialization"
#                   },
#                   {
#                     "id": "fast"
#                   },
#                   {
#                     "id": "messagepack"
#                   },
#                   {
#                     "id": "benchmarkdotnet"
#                   },
#                   {
#                     "id": "net-core"
#                   }
#                 ],
#                 "earnings": {
#                   "total": {
#                     "currencyCode": "USD",
#                     "units": 17,
#                     "nanos": 500000000,
#                     "__typename": "Money"
#                   },
#                   "monthlyEarnings": {
#                     "currencyCode": "USD",
#                     "units": 3,
#                     "nanos": 750000000,
#                     "__typename": "Money"
#                   },
#                   "__typename": "PostEarnings"
#                 },
#                 "creator": {
#                   "id": "6a63927f9b83",
#                   "username": "mvineetsharma",
#                   "name": "Vineet Sharma",
#                   "bio": "",
#                   "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
#                   "twitterScreenName": "VineetSharmaIoT",
#                   "createdAt": 1525616278734
#                 },
#                 "collection": null
#               },
#               "cursor": "40793d1e9f2b"
#             }
#           ],
#           "pageInfo": {
#             "endCursor": "1",
#             "hasNextPage": true
#           }
#         }
#       }
#     }
#   }
# ]
