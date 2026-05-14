# Tasks
1. Create empty notifications.json in data folder, same like stories.json
2. Create endpoints '/notification' and '/notification_medium' in stories.py
3. implement method '/notification' and '/notification_medium' in story_service.py as below
4. Create method 'fetch_notification' like 'fetch_medium_monthly_stats' in medium_api_service.py
a. 'fetch_notification' must fetch notification respons below using the qraph query below 

3. The endpoint '/notification'  in stories.py
a. '/notification_medium' must fecth data from fetch_notification in medium_api_service.py via /notification_medium in story_service.py which add new notification to notifications.json by checking 'data.notificationsConnectionByActivityTypes.notifications.notificationName' and send updates to client

4. Th endpint '/notification_medium'
a. '/notification' must read all notifications.json via '/notification' method in story_service.py and send to client

# Prompt for UI

Now create a new page 'notification' separate  HTML and JS, add it to sidebar. It should have 
1. story-stats-widget at top
2. Notification table with column sorting having following fields with Mapping using /notification endpoint, deffault sort Date most recent first

a. Name - actor.name Link to "https://medium.com/@" + actor.username in new tab, image "https://miro.medium.com/v2/resize:fill:36:36/"+ actor.imageId
b. Date - occurredAt
c. Action - notificationType (users_following_you_rollup and users_following_you= "Follow", post_added_to_catalog = "Added To List", post_recommended = "Clap", users_email_subscribed= "Subscribed")
d. Story - post.title with link post.mediumUrl open in new tab
e. Member - membership.member =Member else "Non Member"
f Auther - verifications.isBookAuthor
3. "Refresh" Notification button to call /notification_medium" and reload the notification list
# Explain implementation details and understanding with exact Response mapping. No code


1. Add 'date' as optional to @router.get("/notification_medium")
2. Modify add methods to start fetching py passing date
3. Add link "Load Older" in at the bottom of Notification table to pass date as oldest date in existing nnotifications
# This includes routs service and medium API methods
explaing the understanding and execution plan, remember the stored date is timestammp and all the way its timestamp, formatting is for display only 
# Grapg Query
```
{
  "operationName": "NotificationsQuery",
  "variables": {
    "activityTypes": null,
    "pagingOptions": {
      "limit": 25,
      "page": null,
      "source": null,
      "to": "1778398756379"
    }
  },
  "query": "query NotificationsQuery($pagingOptions: PagingOptions, $activityTypes: [String!]) {\n  notificationsConnectionByActivityTypes(\n    paging: $pagingOptions\n    activityTypes: $activityTypes\n  ) {\n    notifications {\n      __typename\n      notificationName\n      ...NotificationsList_notification\n    }\n    pagingInfo {\n      next {\n        limit\n        page\n        source\n        to\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment NotificationsList_notification on Notification {\n  __typename\n  ...NotificationQuote_notification\n  ...NotificationResponseDialog_notification\n  ...NotificationResponseCreated_notification\n  ...ActorNotificationLayout_notification\n}\n\nfragment NotificationPostTitle_post on Post {\n  id\n  title\n  __typename\n}\n\nfragment UserAvatar_user on User {\n  id\n  imageId\n  name\n  username\n  __typename\n}\n\nfragment UserAvatarWithBadge_user on User {\n  membership {\n    tier\n    __typename\n    id\n  }\n  ...UserAvatar_user\n  __typename\n  id\n}\n\nfragment userUrl_user on User {\n  __typename\n  id\n  customDomainState {\n    live {\n      domain\n      __typename\n    }\n    __typename\n  }\n  hasSubdomain\n  username\n}\n\nfragment UserAvatarLinkContainer_user on User {\n  ...userUrl_user\n  __typename\n  id\n}\n\nfragment UserAvatarWithBadgeAndLink_user on User {\n  ...UserAvatarWithBadge_user\n  ...UserAvatarLinkContainer_user\n  __typename\n  id\n}\n\nfragment isUserVerifiedBookAuthor_user on User {\n  verifications {\n    isBookAuthor\n    __typename\n  }\n  __typename\n  id\n}\n\nfragment ActorNotificationLayout_user on User {\n  id\n  name\n  ...UserAvatarWithBadgeAndLink_user\n  ...isUserVerifiedBookAuthor_user\n  ...userUrl_user\n  __typename\n}\n\nfragment ActorNotificationLayout_notification on Notification {\n  actor {\n    ...ActorNotificationLayout_user\n    __typename\n    id\n  }\n  rollupItems {\n    actor {\n      id\n      __typename\n    }\n    __typename\n  }\n  isUnread\n  occurredAt\n  notificationType\n  __typename\n}\n\nfragment NotificationQuote_notification on Notification {\n  post {\n    id\n    mediumUrl\n    title\n    visibility\n    ...NotificationPostTitle_post\n    __typename\n  }\n  quote {\n    id\n    startOffset\n    endOffset\n    paragraphs {\n      text\n      type\n      __typename\n    }\n    __typename\n  }\n  ...ActorNotificationLayout_notification\n  __typename\n}\n\nfragment NotificationResponseDetails_post on Post {\n  content {\n    bodyModel {\n      paragraphs {\n        text\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  __typename\n  id\n}\n\nfragment NotificationResponseDialog_notification on Notification {\n  post {\n    id\n    __typename\n  }\n  responsePost {\n    id\n    ...NotificationResponseDetails_post\n    __typename\n  }\n  ...ActorNotificationLayout_notification\n  __typename\n}\n\nfragment NotificationResponseCreated_notification on Notification {\n  post {\n    id\n    ...NotificationPostTitle_post\n    __typename\n  }\n  responsePost {\n    id\n    __typename\n  }\n  ...ActorNotificationLayout_notification\n  __typename\n}"
}
```
# Response
```
{
    "data": {
        "notificationsConnectionByActivityTypes": {
            "notifications": [
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-users_email_subscribed--4ac7fe93a4df",
                    "post": null,
                    "quote": null,
                    "actor": {
                        "id": "4ac7fe93a4df",
                        "name": "Shaun Dunston",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "6a5a41b51410"
                        },
                        "imageId": "0*qN0v1flxVUmNylvR",
                        "username": "djiovani",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778398756342,
                    "notificationType": "users_email_subscribed",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-users_following_you-91040a975037",
                    "post": null,
                    "quote": null,
                    "actor": {
                        "id": "91040a975037",
                        "name": "Paul Hoke",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "c523a1c45360"
                        },
                        "imageId": "1*kLa4bvIY_igZTfmq7CmOGQ.png",
                        "username": "paulhoke",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778393647430,
                    "notificationType": "users_following_you",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_added_to_catalog-8ce6a0f961e6-6a5b9d2bfbc1",
                    "post": {
                        "id": "8ce6a0f961e6",
                        "mediumUrl": "https://mvineetsharma.medium.com/ef-core-json-complex-types-leftjoin-executeupdate-c-14-net-10-upgrade-journey-1-8ce6a0f961e6",
                        "title": "EF Core: JSON Complex Types, LeftJoin & ExecuteUpdate -C# 14 & .NET 10 Upgrade Journey - 1",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "171e808ffc0c",
                        "name": "Andrew",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "8e7f95b899d1"
                        },
                        "imageId": "0*El486jSUF1LqToty",
                        "username": "andrew_62205",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778361872531,
                    "notificationType": "post_added_to_catalog",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_added_to_catalog-f053bdadd99e-d730232f845b",
                    "post": {
                        "id": "f053bdadd99e",
                        "mediumUrl": "https://mvineetsharma.medium.com/11-kafka-design-patterns-for-every-backend-engineer-f053bdadd99e",
                        "title": "11 Kafka Design Patterns for Every Backend Engineer",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "62ebefa7d52",
                        "name": "Biduro maharana",
                        "membership": null,
                        "imageId": "0*pGfgxO4puWjKwH4R",
                        "username": "biduromaharana",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778341020428,
                    "notificationType": "post_added_to_catalog",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_added_to_catalog-b0562c2f51f4-d59334842b5e",
                    "post": {
                        "id": "b0562c2f51f4",
                        "mediumUrl": "https://mvineetsharma.medium.com/api-security-arsenal-real-time-threat-detection-with-apigee-salt-and-cloudflare-b0562c2f51f4",
                        "title": "API Security Arsenal: Real-Time Threat Detection with Apigee, Salt, and Cloudflare",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "ab62900a04f6",
                        "name": "Francisco Barbosa",
                        "membership": null,
                        "imageId": "0*mgtBuDSUpEN21c_y",
                        "username": "fcobarbosa2007",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778340474904,
                    "notificationType": "post_added_to_catalog",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_added_to_catalog-13aae317b1c4-b7547b74f27d",
                    "post": {
                        "id": "13aae317b1c4",
                        "mediumUrl": "https://mvineetsharma.medium.com/10-essential-microservices-architecture-patterns-a-professional-reference-architecture-with-net-13aae317b1c4",
                        "title": "10 Microservices Architecture Patterns: A Reference Architecture with .NET and Azure — Part 1",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "8d8349efc579",
                        "name": "BiserRs",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "0f297837-d79f-49fd-978c-4f8a9cbdc867"
                        },
                        "imageId": "0*9bqHOfSZ5a36zPN3",
                        "username": "bisetrs",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778319485716,
                    "notificationType": "post_added_to_catalog",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-users_following_you-5f00a04ec92c",
                    "post": null,
                    "quote": null,
                    "actor": {
                        "id": "5f00a04ec92c",
                        "name": "Giovanni Di Guardo",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "37e9acff-5530-43f4-bbde-52a4a0a90ef2"
                        },
                        "imageId": "0*N0KIs4GX22R6jS-F.",
                        "username": "giovannidiguardo",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [
                        {
                            "actor": {
                                "id": "5f00a04ec92c",
                                "__typename": "User"
                            },
                            "__typename": "Notification"
                        },
                        {
                            "actor": {
                                "id": "c449118ded03",
                                "__typename": "User"
                            },
                            "__typename": "Notification"
                        }
                    ],
                    "isUnread": false,
                    "occurredAt": 1778310228353,
                    "notificationType": "users_following_you_rollup",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-users_email_subscribed--5f00a04ec92c",
                    "post": null,
                    "quote": null,
                    "actor": {
                        "id": "5f00a04ec92c",
                        "name": "Giovanni Di Guardo",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "37e9acff-5530-43f4-bbde-52a4a0a90ef2"
                        },
                        "imageId": "0*N0KIs4GX22R6jS-F.",
                        "username": "giovannidiguardo",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [
                        {
                            "actor": {
                                "id": "5f00a04ec92c",
                                "__typename": "User"
                            },
                            "__typename": "Notification"
                        },
                        {
                            "actor": {
                                "id": "c449118ded03",
                                "__typename": "User"
                            },
                            "__typename": "Notification"
                        }
                    ],
                    "isUnread": false,
                    "occurredAt": 1778310228309,
                    "notificationType": "users_email_subscribed",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-41cc12760d67-78d658ed2c7",
                    "post": {
                        "id": "41cc12760d67",
                        "mediumUrl": "https://mvineetsharma.medium.com/real-time-push-without-the-headache-server-sent-events-sse-in-net-10-vehixcare-platform-41cc12760d67",
                        "title": "Real-Time Push Without the Headache: Server-Sent Events (SSE) in .NET 10 - Vehixcare Platform",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "78d658ed2c7",
                        "name": "王朝松",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "d23cf0976185"
                        },
                        "imageId": "0*dL5bubbYN-GtjCDI",
                        "username": "Auiokm",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778305712374,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_added_to_catalog-30dd7aa4eba0-3a6ad144c135",
                    "post": {
                        "id": "30dd7aa4eba0",
                        "mediumUrl": "https://mvineetsharma.medium.com/ai-fluency-50-terms-you-actually-need-30dd7aa4eba0",
                        "title": "AI Fluency: 50 Terms You Actually Need",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "bb4c280a214a",
                        "name": "Francisco de Jesús Orozco Ruiz",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "3596e144-d6b1-4635-ae25-b40bf138b8df"
                        },
                        "imageId": "1*e_RxJ-HU9QM6vjt0bRN6Tw.png",
                        "username": "fjor_5979",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778282727329,
                    "notificationType": "post_added_to_catalog",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_added_to_catalog-3fa6595a5063-648b82deff98",
                    "post": {
                        "id": "3fa6595a5063",
                        "mediumUrl": "https://mvineetsharma.medium.com/dev-setup-real-time-ui-on-android-ios-with-signalr-spotify-clone-with-flutter-and-net-10-3fa6595a5063",
                        "title": "Dev Setup: Real-time UI on Android + iOS with SignalR - Spotify Clone With Flutter And .NET 10",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "b28951e3d307",
                        "name": "Kadir İlhan",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "e994fecfef18"
                        },
                        "imageId": "0*-ar4-L4L8oAq2zBU",
                        "username": "kadirilhan61",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778279004675,
                    "notificationType": "post_added_to_catalog",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-cc505a08441b-49c5200dbc2",
                    "post": {
                        "id": "cc505a08441b",
                        "mediumUrl": "https://mvineetsharma.medium.com/spotify-clone-with-flutter-and-net-10-4-parts-series-cc505a08441b",
                        "title": "Spotify Clone With Flutter And .NET 10 - 4 Parts Series",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "49c5200dbc2",
                        "name": "Ronaldo Araujo",
                        "membership": null,
                        "imageId": "1*lLjWq-H4uc_-42L_nGKFMQ.jpeg",
                        "username": "ronaldo.as",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778275204133,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-dced71a68a52-49c5200dbc2",
                    "post": {
                        "id": "dced71a68a52",
                        "mediumUrl": "https://mvineetsharma.medium.com/clean-architecture-anti-pattern-exception-a-net-developers-guide-part-1-dced71a68a52",
                        "title": "Clean Architecture Anti-Pattern -  Exception: A .NET Developer’s Guide - Part 1",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "49c5200dbc2",
                        "name": "Ronaldo Araujo",
                        "membership": null,
                        "imageId": "1*lLjWq-H4uc_-42L_nGKFMQ.jpeg",
                        "username": "ronaldo.as",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778270373212,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-a1f6ea3a0916-49c5200dbc2",
                    "post": {
                        "id": "a1f6ea3a0916",
                        "mediumUrl": "https://mvineetsharma.medium.com/file-based-apps-run-single-cs-file-fast-prototyping-c-14-net-10-part-2-a1f6ea3a0916",
                        "title": "File-Based Apps: Run Single CS File, Fast Prototyping - C# 14 & .NET 10 Upgrade Journey - 2",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "49c5200dbc2",
                        "name": "Ronaldo Araujo",
                        "membership": null,
                        "imageId": "1*lLjWq-H4uc_-42L_nGKFMQ.jpeg",
                        "username": "ronaldo.as",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778269648845,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-68ec3e58c0d8-49c5200dbc2",
                    "post": {
                        "id": "68ec3e58c0d8",
                        "mediumUrl": "https://mvineetsharma.medium.com/20-tiers-150-checks-net-code-review-mastery-series-68ec3e58c0d8",
                        "title": "20 Tiers 150+ Checks — .NET Code Review Mastery Series",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "49c5200dbc2",
                        "name": "Ronaldo Araujo",
                        "membership": null,
                        "imageId": "1*lLjWq-H4uc_-42L_nGKFMQ.jpeg",
                        "username": "ronaldo.as",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778266632063,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-884985da94f7-415c5810e75a",
                    "post": {
                        "id": "884985da94f7",
                        "mediumUrl": "https://mvineetsharma.medium.com/design-patterns-part-1-redefining-design-patterns-884985da94f7",
                        "title": "Design Patterns: Part 1 — Redefining Design Patterns",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "415c5810e75a",
                        "name": "Erik de la cerda andrade",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "a736a789-a498-4d12-afb8-230e4f650f48"
                        },
                        "imageId": "0*mmr1TpvKmSdyhMoU.jpg",
                        "username": "erik24.03",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778257427617,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-756e388c730b-49c5200dbc2",
                    "post": {
                        "id": "756e388c730b",
                        "mediumUrl": "https://mvineetsharma.medium.com/architecture-core-building-blocks-living-cluster-nodes-pods-control-plane-k8s-unlocked-756e388c730b",
                        "title": "Architecture & Core Building Blocks: Living Cluster - Nodes, Pods & Control Plane - K8s Unlocked",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "49c5200dbc2",
                        "name": "Ronaldo Araujo",
                        "membership": null,
                        "imageId": "1*lLjWq-H4uc_-42L_nGKFMQ.jpeg",
                        "username": "ronaldo.as",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778252495382,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_added_to_catalog-16ed6be3b9ca-a3fe7a4f4016",
                    "post": {
                        "id": "16ed6be3b9ca",
                        "mediumUrl": "https://mvineetsharma.medium.com/docker-podman-and-kubernetes-from-containers-to-cloud-native-reality-16ed6be3b9ca",
                        "title": "Docker, Podman, and Kubernetes: From Containers to Cloud-Native Reality",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "5c41a3fc719b",
                        "name": "Ridwangsn",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "a22db6275d4d"
                        },
                        "imageId": "0*eSY-f4KgSsYV9KJp",
                        "username": "ridwangsn",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778241051223,
                    "notificationType": "post_added_to_catalog",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-429025331eee-49c5200dbc2",
                    "post": {
                        "id": "429025331eee",
                        "mediumUrl": "https://mvineetsharma.medium.com/angular-components-modules-dependency-injection-templates-pipes-directives-evolution-429025331eee",
                        "title": "Angular Components, Modules, Dependency Injection, Templates, Pipes, Directives - Evolution",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "49c5200dbc2",
                        "name": "Ronaldo Araujo",
                        "membership": null,
                        "imageId": "1*lLjWq-H4uc_-42L_nGKFMQ.jpeg",
                        "username": "ronaldo.as",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778240848235,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-post_recommended-0ed3462c2cf9-b3293c306089",
                    "post": {
                        "id": "0ed3462c2cf9",
                        "mediumUrl": "https://mvineetsharma.medium.com/solid-principles-building-spotifys-unshakable-foundation-0ed3462c2cf9",
                        "title": "SOLID Principles: Building Spotify’s Unshakable Foundation",
                        "visibility": "LOCKED",
                        "__typename": "Post"
                    },
                    "quote": null,
                    "actor": {
                        "id": "b3293c306089",
                        "name": "Zahid Tanveer",
                        "membership": {
                            "tier": "MEMBER",
                            "__typename": "Membership",
                            "id": "57547c4b2b92"
                        },
                        "imageId": "1*HK-bIx7Zaxxwm64qno3f9A.png",
                        "username": "zahid_tanveer",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778237648023,
                    "notificationType": "post_recommended",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-users_following_you-8a3b41041fda",
                    "post": null,
                    "quote": null,
                    "actor": {
                        "id": "8a3b41041fda",
                        "name": "Manoj Kumar Sharma",
                        "membership": null,
                        "imageId": "",
                        "username": "mcitp.ms09",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [
                        {
                            "actor": {
                                "id": "8a3b41041fda",
                                "__typename": "User"
                            },
                            "__typename": "Notification"
                        },
                        {
                            "actor": {
                                "id": "6f9a52ff57de",
                                "__typename": "User"
                            },
                            "__typename": "Notification"
                        }
                    ],
                    "isUnread": false,
                    "occurredAt": 1778217854243,
                    "notificationType": "users_following_you_rollup",
                    "responsePost": null
                },
                {
                    "__typename": "Notification",
                    "notificationName": "6a63927f9b83-users_email_subscribed--8a3b41041fda",
                    "post": null,
                    "quote": null,
                    "actor": {
                        "id": "8a3b41041fda",
                        "name": "Manoj Kumar Sharma",
                        "membership": null,
                        "imageId": "",
                        "username": "mcitp.ms09",
                        "__typename": "User",
                        "customDomainState": null,
                        "hasSubdomain": false,
                        "verifications": {
                            "isBookAuthor": false,
                            "__typename": "VerifiedInfo"
                        }
                    },
                    "rollupItems": [],
                    "isUnread": false,
                    "occurredAt": 1778217854215,
                    "notificationType": "users_email_subscribed",
                    "responsePost": null
                }
            ],
            "pagingInfo": {
                "next": {
                    "limit": 25,
                    "page": null,
                    "source": null,
                    "to": "1778212629383",
                    "__typename": "PageParams"
                },
                "__typename": "Paging"
            },
            "__typename": "NotificationsConnection"
        }
    }
}
```