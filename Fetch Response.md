## Lifetime Fetch Request
```
fetch("https://medium.com/_/graphql", {
  "headers": {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "apollographql-client-name": "lite",
    "apollographql-client-version": "main-20260407-133539-7d466fcf98",
    "content-type": "application/json",
    "graphql-operation": "useStatsPostNewChartDataQuery",
    "medium-frontend-app": "lite/main-20260407-133539-7d466fcf98",
    "medium-frontend-path": "/me/stats/post/4f4fbc87426d",
    "medium-frontend-route": "stats-post",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    "sec-ch-ua-arch": "\"x86\"",
    "sec-ch-ua-bitness": "\"64\"",
    "sec-ch-ua-full-version": "\"143.0.7499.146\"",
    "sec-ch-ua-full-version-list": "\"Google Chrome\";v=\"143.0.7499.146\", \"Chromium\";v=\"143.0.7499.146\", \"Not A(Brand\";v=\"24.0.0.0\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": "\"\"",
    "sec-ch-ua-platform": "\"Linux\"",
    "sec-ch-ua-platform-version": "\"6.17.0\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
  },
  "referrer": "https://medium.com/me/stats/post/4f4fbc87426d",
  "body": "[{\"operationName\":\"useStatsPostNewChartDataQuery\",\"variables\":{\"postId\":\"4f4fbc87426d\",\"startAt\":1775520000000,\"endAt\":1775606400000,\"postStatsDailyBundleInput\":{\"postId\":\"4f4fbc87426d\",\"fromDayStartsAt\":1775520000useStatsPostNewChartDataQuery000,\"toDayStartsAt\":1775520000000}},\"query\":\"query ($postId: ID!, $startAt: Long!, $endAt: Long!, $postStatsDailyBundleInput: PostStatsDailyBundleInput!) {\\n  post(id: $postId) {\\n    id\\n    earnings {\\n      dailyEarnings(startAt: $startAt, endAt: $endAt) {\\n        ...newBucketTimestamps_dailyPostEarning\\n        __typename\\n      }\\n      __typename\\n    }\\n    publicationFeaturingEventsConnection(first: 25, after: \\\"\\\") {\\n      ... on PublicationFeaturingEventsConnection {\\n        edges {\\n          node {\\n            eventType\\n            occurredAt\\n            __typename\\n          }\\n          __typename\\n        }\\n        __typename\\n      }\\n      __typename\\n    }\\n    __typename\\n  }\\n  postStatsDailyBundle(postStatsDailyBundleInput: $postStatsDailyBundleInput) {\\n    buckets {\\n      ...newBucketTimestamps_postStatsDailyBundleBucket\\n      __typename\\n    }\\n    __typename\\n  }\\n}\\n\\nfragment newBucketTimestamps_dailyPostEarning on DailyPostEarning {\\n  periodStartedAt\\n  amount\\n  __typename\\n}\\n\\nfragment newBucketTimestamps_postStatsDailyBundleBucket on PostStatsDailyBundleBucket {\\n  dayStartsAt\\n  membershipType\\n  readersThatReadCount\\n  readersThatViewedCount\\n  readersThatClappedCount\\n  readersThatRepliedCount\\n  readersThatHighlightedCount\\n  readersThatInitiallyFollowedAuthorFromThisPostCount\\n  __typename\\n}\\n\"}]",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
});
```

## Fetch Source code 
```
query = """query StatsPostFunnelQuery($postStatsTotalBundleInput: PostStatsTotalBundleInput!) {
  postStatsTotalBundle(postStatsTotalBundleInput: $postStatsTotalBundleInput) {
    post {
      id
      firstPublishedAt
      clapCount
      readingTime
      uniqueSlug
      tags{id}

      collection {
            id
            name
            slug
            domain
            description
            avatar {
            id
            __typename
            }
            subscriberCount
        
            __typename
        }
      
      __typename
    }
    
    
    readersCount
    viewersCount
    feedClickThroughRate
    presentationCount
    __typename
  }
}"""

        variables = {
            "postStatsTotalBundleInput": {
                "postId": post_id
            }
        }

        payload = self._build_graphql_request("StatsPostFunnelQuery", variables query, post_id, "stats-post")
        headers = self._get_common_headers(post_id, "StatsPostFunnelQuery")
        return self._make_request(self.GRAPHQL_URL, headers, payload, "Lifetime Stats")


```
## Request Payload
``` 
[
  {
    "operationName": "StatsPostFunnelQuery",
    "variables": {
      "postStatsTotalBundleInput": {
        "postId": "dddc86088f5e"
      }
    },
    "query": "query StatsPostFunnelQuery($postStatsTotalBundleInput: PostStatsTotalBundleInput!) {\n  postStatsTotalBundle(postStatsTotalBundleInput: $postStatsTotalBundleInput) {\n    post {\n      id\n      firstPublishedAt\n      clapCount\n      readingTime\n      uniqueSlug\n      tags{id}\n\n      collection {\n            id\n            name\n            slug\n            domain\n            description\n            avatar {\n            id\n            __typename\n            }\n            subscriberCount\n        \n            __typename\n        }\n      \n      __typename\n    }\n    \n    \n    readersCount\n    viewersCount\n    feedClickThroughRate\n    presentationCount\n    __typename\n  }\n}"
  }
]


```

## Fetch Response
```
[
  {
    "data": {
      "postStatsTotalBundle": {
        "post": {
          "id": "dddc86088f5e",
          "firstPublishedAt": 1705911793148,
          "clapCount": 0,
          "readingTime": 5.1773584905660375,
          "uniqueSlug": "code-smell-practical-guide-using-net-core-part-iii-dddc86088f5e",
          "tags": [
            {
              "id": "code-smells"
            },
            {
              "id": "data-clumps"
            },
            {
              "id": "shotgun-surgery"
            },
            {
              "id": "lazy-class"
            },
            {
              "id": "speculative-generality"
            }
          ],
          "collection": {
            "id": "4e2c1156667e",
            "name": "Dev Genius",
            "slug": "dev-genius",
            "domain": "blog.devgenius.io",
            "description": "Coding, Tutorials, News, UX, UI and much more related to development",
            "avatar": {
              "id": "1*CvejhRq3NYsivxILYXEdfA.jpeg",
              "__typename": "ImageMetadata"
            },
            "subscriberCount": 31446,
            "__typename": "Collection"
          },
          "__typename": "Post"
        },
        "readersCount": 12,
        "viewersCount": 23,
        "feedClickThroughRate": null,
        "presentationCount": null,
        "__typename": "PostStatsTotalBundle"
      }
    }
  }
]

``` 

## Partner Progam Frtch
```
fetch("https://medium.com/_/graphql", {
  "headers": {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "apollographql-client-name": "lite",
    "apollographql-client-version": "main-20260407-133539-7d466fcf98",
    "content-type": "application/json",
    "graphql-operation": "StoryEarningsQuery",
    "medium-frontend-app": "lite/main-20260407-133539-7d466fcf98",
    "medium-frontend-path": "/me/partner/dashboard",
    "medium-frontend-route": "ShowPartnerDashboard",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    "sec-ch-ua-arch": "\"x86\"",
    "sec-ch-ua-bitness": "\"64\"",
    "sec-ch-ua-full-version": "\"143.0.7499.146\"",
    "sec-ch-ua-full-version-list": "\"Google Chrome\";v=\"143.0.7499.146\", \"Chromium\";v=\"143.0.7499.146\", \"Not A(Brand\";v=\"24.0.0.0\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": "\"\"",
    "sec-ch-ua-platform": "\"Linux\"",
    "sec-ch-ua-platform-version": "\"6.17.0\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin"
  },
  "referrer": "https://medium.com/me/partner/dashboard",
  "body": "[{\"operationName\":\"StoryEarningsQuery\",\"variables\":{\"username\":\"mvineetsharma\",\"first\":10,\"after\":\"\",\"startAt\":1772323200000,\"endAt\":1775001600000},\"query\":\"query StoryEarningsQuery($username: ID!, $first: Int!, $after: String!, $startAt: Long!, $endAt: Long!) {\\n  userResult(username: $username) {\\n    __typename\\n    ... on User {\\n      id\\n      postsConnection(\\n        first: $first\\n        after: $after\\n        orderBy: {lifetimeEarnings: DESC}\\n        filter: {published: true}\\n        timeRange: {startAt: $startAt, endAt: $endAt}\\n      ) {\\n        __typename\\n        edges {\\n          node {\\n            ...StoryEarningsTable_post\\n            ...MobileStoryEarningsTable_post\\n            __typename\\n          }\\n          __typename\\n        }\\n        pageInfo {\\n          endCursor\\n          hasNextPage\\n          __typename\\n        }\\n      }\\n      __typename\\n    }\\n  }\\n}\\n\\nfragment moneyUtils_money on Money {\\n  currencyCode\\n  nanos\\n  units\\n  __typename\\n}\\n\\nfragment userUrl_user on User {\\n  __typename\\n  id\\n  customDomainState {\\n    live {\\n      domain\\n      __typename\\n    }\\n    __typename\\n  }\\n  hasSubdomain\\n  username\\n}\\n\\nfragment usePostUrl_post on Post {\\n  id\\n  creator {\\n    ...userUrl_user\\n    __typename\\n    id\\n  }\\n  collection {\\n    id\\n    domain\\n    slug\\n    __typename\\n  }\\n  isSeries\\n  mediumUrl\\n  sequence {\\n    slug\\n    __typename\\n  }\\n  uniqueSlug\\n  __typename\\n}\\n\\nfragment Star_post on Post {\\n  id\\n  __typename\\n}\\n\\nfragment UserAvatar_user on User {\\n  __typename\\n  id\\n  imageId\\n  membership {\\n    tier\\n    __typename\\n    id\\n  }\\n  name\\n  username\\n  ...userUrl_user\\n}\\n\\nfragment PostPreviewBylineAuthorAvatar_user on User {\\n  ...UserAvatar_user\\n  __typename\\n  id\\n}\\n\\nfragment isUserVerifiedBookAuthor_user on User {\\n  verifications {\\n    isBookAuthor\\n    __typename\\n  }\\n  __typename\\n  id\\n}\\n\\nfragment UserLink_user on User {\\n  ...userUrl_user\\n  __typename\\n  id\\n}\\n\\nfragment UserName_user on User {\\n  id\\n  name\\n  ...isUserVerifiedBookAuthor_user\\n  ...UserLink_user\\n  __typename\\n}\\n\\nfragment PostPreviewByLineAuthor_user on User {\\n  ...PostPreviewBylineAuthorAvatar_user\\n  ...UserName_user\\n  __typename\\n  id\\n}\\n\\nfragment collectionUrl_collection on Collection {\\n  id\\n  domain\\n  slug\\n  __typename\\n}\\n\\nfragment CollectionAvatar_collection on Collection {\\n  name\\n  avatar {\\n    id\\n    __typename\\n  }\\n  ...collectionUrl_collection\\n  __typename\\n  id\\n}\\n\\nfragment SignInOptions_collection on Collection {\\n  id\\n  name\\n  __typename\\n}\\n\\nfragment SignUpOptions_collection on Collection {\\n  id\\n  name\\n  __typename\\n}\\n\\nfragment SusiModal_collection on Collection {\\n  name\\n  ...SignInOptions_collection\\n  ...SignUpOptions_collection\\n  __typename\\n  id\\n}\\n\\nfragment PublicationFollowButton_collection on Collection {\\n  id\\n  slug\\n  name\\n  ...SusiModal_collection\\n  __typename\\n}\\n\\nfragment EntityPresentationRankedModulePublishingTracker_entity on RankedModulePublishingEntity {\\n  __typename\\n  ... on Collection {\\n    id\\n    __typename\\n  }\\n  ... on User {\\n    id\\n    __typename\\n  }\\n}\\n\\nfragment CollectionTooltip_collection on Collection {\\n  id\\n  name\\n  slug\\n  description\\n  subscriberCount\\n  customStyleSheet {\\n    header {\\n      backgroundImage {\\n        id\\n        __typename\\n      }\\n      __typename\\n    }\\n    __typename\\n    id\\n  }\\n  ...CollectionAvatar_collection\\n  ...PublicationFollowButton_collection\\n  ...EntityPresentationRankedModulePublishingTracker_entity\\n  __typename\\n}\\n\\nfragment CollectionLinkWithPopover_collection on Collection {\\n  name\\n  ...collectionUrl_collection\\n  ...CollectionTooltip_collection\\n  __typename\\n  id\\n}\\n\\nfragment PostPreviewByLineCollection_collection on Collection {\\n  ...CollectionAvatar_collection\\n  ...CollectionTooltip_collection\\n  ...CollectionLinkWithPopover_collection\\n  __typename\\n  id\\n}\\n\\nfragment PostPreviewByLine_post on Post {\\n  creator {\\n    ...PostPreviewByLineAuthor_user\\n    __typename\\n    id\\n  }\\n  collection {\\n    ...PostPreviewByLineCollection_collection\\n    __typename\\n    id\\n  }\\n  __typename\\n  id\\n}\\n\\nfragment TablePostInfos_post on Post {\\n  id\\n  title\\n  readingTime\\n  isLocked\\n  visibility\\n  firstBoostedAt\\n  ...usePostUrl_post\\n  ...Star_post\\n  ...PostPreviewByLine_post\\n  __typename\\n}\\n\\nfragment usePostStatsUrl_post on Post {\\n  id\\n  creator {\\n    id\\n    username\\n    __typename\\n  }\\n  __typename\\n}\\n\\nfragment StoryEarningsTableRow_post on Post {\\n  id\\n  firstPublishedAt\\n  earnings {\\n    monthlyEarnings: total(input: {between: {startAt: $startAt, endAt: $endAt}}) {\\n      ...moneyUtils_money\\n      __typename\\n    }\\n    lifetimeEarnings: total {\\n      currencyCode\\n      ...moneyUtils_money\\n      __typename\\n    }\\n    __typename\\n  }\\n  ...TablePostInfos_post\\n  ...usePostStatsUrl_post\\n  __typename\\n}\\n\\nfragment StoryEarningsTable_post on Post {\\n  id\\n  ...StoryEarningsTableRow_post\\n  __typename\\n}\\n\\nfragment MobileStoryEarningsTable_post on Post {\\n  id\\n  firstPublishedAt\\n  earnings {\\n    monthlyEarnings: total(input: {between: {startAt: $startAt, endAt: $endAt}}) {\\n      ...moneyUtils_money\\n      __typename\\n    }\\n    lifetimeEarnings: total {\\n      currencyCode\\n      ...moneyUtils_money\\n      __typename\\n    }\\n    __typename\\n  }\\n  ...TablePostInfos_post\\n  ...usePostStatsUrl_post\\n  __typename\\n}\\n\"}]",
  "method": "POST",
  "mode": "cors",
  "credentials": "include"
});
```
## Response
```
[
    {
        "data": {
            "userResult": {
                "__typename": "User",
                "id": "6a63927f9b83",
                "postsConnection": {
                    "__typename": "RelayPostConnection",
                    "edges": [
                        {
                            "node": {
                                "id": "6b9276cf73a1",
                                "firstPublishedAt": 1771863180772,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 630000000,
                                        "units": 7,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 950000000,
                                        "units": 7,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "Distinguishing Infrastructure & Domain Exceptions in .NET - Part 1",
                                "readingTime": 10.018867924528301,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": {
                                    "id": "4e2c1156667e",
                                    "domain": "blog.devgenius.io",
                                    "slug": "dev-genius",
                                    "__typename": "Collection",
                                    "name": "Dev Genius",
                                    "avatar": {
                                        "id": "1*CvejhRq3NYsivxILYXEdfA.jpeg",
                                        "__typename": "ImageMetadata"
                                    },
                                    "description": "Coding, Tutorials, News, UX, UI and much more related to development",
                                    "subscriberCount": 31450,
                                    "customStyleSheet": null
                                },
                                "isSeries": false,
                                "mediumUrl": "https://blog.devgenius.io/distinguishing-infrastructure-exceptions-from-domain-exceptions-in-net-6b9276cf73a1",
                                "sequence": null,
                                "uniqueSlug": "distinguishing-infrastructure-exceptions-from-domain-exceptions-in-net-6b9276cf73a1",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "40793d1e9f2b",
                                "firstPublishedAt": 1746026444668,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 710000000,
                                        "units": 5,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 460000000,
                                        "units": 9,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "Achieving 10x Faster Serialization in .NET Core",
                                "readingTime": 4.8437106918239,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": null,
                                "isSeries": false,
                                "mediumUrl": "https://mvineetsharma.medium.com/achieving-10x-faster-serialization-in-net-core-40793d1e9f2b",
                                "sequence": null,
                                "uniqueSlug": "achieving-10x-faster-serialization-in-net-core-40793d1e9f2b",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "139f1dce67da",
                                "firstPublishedAt": 1772020529781,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 380000000,
                                        "units": 2,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 630000000,
                                        "units": 2,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "Modernizing the Monolith: Migration Strategy & .NET 10 Architecture — Part 1",
                                "readingTime": 11.379559748427672,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": {
                                    "id": "4e2c1156667e",
                                    "domain": "blog.devgenius.io",
                                    "slug": "dev-genius",
                                    "__typename": "Collection",
                                    "name": "Dev Genius",
                                    "avatar": {
                                        "id": "1*CvejhRq3NYsivxILYXEdfA.jpeg",
                                        "__typename": "ImageMetadata"
                                    },
                                    "description": "Coding, Tutorials, News, UX, UI and much more related to development",
                                    "subscriberCount": 31450,
                                    "customStyleSheet": null
                                },
                                "isSeries": false,
                                "mediumUrl": "https://blog.devgenius.io/modernizing-the-monolith-migration-strategy-net-10-architecture-part-1-139f1dce67da",
                                "sequence": null,
                                "uniqueSlug": "modernizing-the-monolith-migration-strategy-net-10-architecture-part-1-139f1dce67da",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "78cb972195da",
                                "firstPublishedAt": 1774594720011,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 210000000,
                                        "units": 1,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 0,
                                        "units": 2,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "ASP.NET Core Filters Deep Dive: Building Maintainable Web APIs with .NET 10 and Reactive Extensions",
                                "readingTime": 21.256603773584903,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": null,
                                "isSeries": false,
                                "mediumUrl": "https://mvineetsharma.medium.com/asp-net-core-filters-deep-dive-building-maintainable-web-apis-with-net-10-and-reactive-extensions-78cb972195da",
                                "sequence": null,
                                "uniqueSlug": "asp-net-core-filters-deep-dive-building-maintainable-web-apis-with-net-10-and-reactive-extensions-78cb972195da",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "44ba9ef608e4",
                                "firstPublishedAt": 1769105832089,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 740000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 210000000,
                                        "units": 1,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "Tuning Connection Pools for a 10,000 RPS .NET Core API — .Net 10 Update",
                                "readingTime": 6.932075471698113,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": {
                                    "id": "4e2c1156667e",
                                    "domain": "blog.devgenius.io",
                                    "slug": "dev-genius",
                                    "__typename": "Collection",
                                    "name": "Dev Genius",
                                    "avatar": {
                                        "id": "1*CvejhRq3NYsivxILYXEdfA.jpeg",
                                        "__typename": "ImageMetadata"
                                    },
                                    "description": "Coding, Tutorials, News, UX, UI and much more related to development",
                                    "subscriberCount": 31450,
                                    "customStyleSheet": null
                                },
                                "isSeries": false,
                                "mediumUrl": "https://blog.devgenius.io/tuning-connection-pools-for-a-10-000-rps-net-core-api-44ba9ef608e4",
                                "sequence": null,
                                "uniqueSlug": "tuning-connection-pools-for-a-10-000-rps-net-core-api-44ba9ef608e4",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "3bc76ce78c56",
                                "firstPublishedAt": 1771445268330,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 650000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 850000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "Why ASP.NET Core 10 Reactive Applications Fail in Production: Pitfalls & Solutions in Azure Cloud",
                                "readingTime": 23.73427672955975,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": {
                                    "id": "4e2c1156667e",
                                    "domain": "blog.devgenius.io",
                                    "slug": "dev-genius",
                                    "__typename": "Collection",
                                    "name": "Dev Genius",
                                    "avatar": {
                                        "id": "1*CvejhRq3NYsivxILYXEdfA.jpeg",
                                        "__typename": "ImageMetadata"
                                    },
                                    "description": "Coding, Tutorials, News, UX, UI and much more related to development",
                                    "subscriberCount": 31450,
                                    "customStyleSheet": null
                                },
                                "isSeries": false,
                                "mediumUrl": "https://blog.devgenius.io/why-asp-net-core-10-reactive-applications-fail-in-production-pitfalls-solutions-in-azure-cloud-3bc76ce78c56",
                                "sequence": null,
                                "uniqueSlug": "why-asp-net-core-10-reactive-applications-fail-in-production-pitfalls-solutions-in-azure-cloud-3bc76ce78c56",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "d5b09b962edc",
                                "firstPublishedAt": 1774204367126,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 580000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 90000000,
                                        "units": 1,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "Architectural Remediation Framework: Eliminating the 12 Silent Killers in .NET 10 Web APIs — Part 1",
                                "readingTime": 28.254716981132077,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": null,
                                "isSeries": false,
                                "mediumUrl": "https://mvineetsharma.medium.com/architectural-remediation-framework-eliminating-the-12-silent-killers-in-net-10-web-apis-part-1-d5b09b962edc",
                                "sequence": null,
                                "uniqueSlug": "architectural-remediation-framework-eliminating-the-12-silent-killers-in-net-10-web-apis-part-1-d5b09b962edc",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "6fa47bbb8e97",
                                "firstPublishedAt": 1770630914549,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 580000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 30000000,
                                        "units": 1,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "Implementing Clean Architecture with Vertical Slice Architecture in .NET 8",
                                "readingTime": 14.877358490566039,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": null,
                                "isSeries": false,
                                "mediumUrl": "https://mvineetsharma.medium.com/implementing-clean-architecture-with-vertical-slice-architecture-in-net-8-6fa47bbb8e97",
                                "sequence": null,
                                "uniqueSlug": "implementing-clean-architecture-with-vertical-slice-architecture-in-net-8-6fa47bbb8e97",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "13aae317b1c4",
                                "firstPublishedAt": 1773702853018,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 400000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 500000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "10 Microservices Architecture Patterns: A Reference Architecture with .NET and Azure — Part 1",
                                "readingTime": 32.447169811320755,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": null,
                                "isSeries": false,
                                "mediumUrl": "https://mvineetsharma.medium.com/10-essential-microservices-architecture-patterns-a-professional-reference-architecture-with-net-13aae317b1c4",
                                "sequence": null,
                                "uniqueSlug": "10-essential-microservices-architecture-patterns-a-professional-reference-architecture-with-net-13aae317b1c4",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        },
                        {
                            "node": {
                                "id": "de5ed25bb135",
                                "firstPublishedAt": 1772107613162,
                                "earnings": {
                                    "monthlyEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 380000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "lifetimeEarnings": {
                                        "currencyCode": "USD",
                                        "nanos": 950000000,
                                        "units": 0,
                                        "__typename": "Money"
                                    },
                                    "__typename": "PostEarnings"
                                },
                                "title": "Zero to Production: .NET in 2026: 35 Lessons on How to Master the Stack with .NET 10 and Azure",
                                "readingTime": 54.703773584905655,
                                "isLocked": true,
                                "visibility": "LOCKED",
                                "firstBoostedAt": null,
                                "creator": {
                                    "__typename": "User",
                                    "id": "6a63927f9b83",
                                    "customDomainState": {
                                        "live": {
                                            "domain": "mvineetsharma.medium.com",
                                            "__typename": "CustomDomain"
                                        },
                                        "__typename": "CustomDomainState"
                                    },
                                    "hasSubdomain": true,
                                    "username": "mvineetsharma",
                                    "imageId": "1*u0kG3U0iiFtJZ4gYQPH4xQ.png",
                                    "membership": null,
                                    "name": "Vineet Sharma",
                                    "verifications": {
                                        "isBookAuthor": false,
                                        "__typename": "VerifiedInfo"
                                    }
                                },
                                "collection": null,
                                "isSeries": false,
                                "mediumUrl": "https://mvineetsharma.medium.com/zero-to-production-net-in-2026-35-lessons-on-how-to-master-the-stack-with-net-10-and-azure-de5ed25bb135",
                                "sequence": null,
                                "uniqueSlug": "zero-to-production-net-in-2026-35-lessons-on-how-to-master-the-stack-with-net-10-and-azure-de5ed25bb135",
                                "__typename": "Post"
                            },
                            "__typename": "RelayPostEdge"
                        }
                    ],
                    "pageInfo": {
                        "endCursor": "10",
                        "hasNextPage": true,
                        "__typename": "PageInfoV2"
                    }
                }
            }
        }
    }
]
```