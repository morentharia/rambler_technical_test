# rambler_technical_test

простой telnet чат

пример использования.

```
+--------------------------------------------------------------------------------------------------------------------+
|                                                                                                                    |
| $ pip install -r requirements.txt && python server.py --port=2323                                                  |
|                                                                                                                    |
+----------------------------------------------------------+---------------------------------------------------------+
| $ telnet localhost 2323                                  |                                                         |
| Trying 127.0.0.1...                                      |                                                         |
| Connected to localhost.                                  |                                                         |
| Escape character is '^]'.                                |                                                         |
| login frank                                              |                                                         |
| *** User change nick anonymous --> frank                 |                                                         |
| join frank_talk                                          |                                                         |
| *** #frank_talk history                                  |                                                         |
| *** User frank joined room #frank_talk                   |  $ telnet localhost 2323                                |
| i think you need to tank to frank...                     |  Trying 127.0.0.1...                                    |
| #frank_talk:frank> i think you need to tank to frank...  |  Connected to localhost.                                |
| frank frank frank                                        |  Escape character is '^]'.                              |
| #frank_talk:frank> frank frank frank                     |  login me                                               |
| *** User change nick anonymous --> me                    |  *** User change nick anonymous --> me                  |
| *** User me joined room #frank_talk                      |  join #frank_talk                                       |
|                                                          |  *** #frank_talk history                                |
|                                                          |  #frank_talk:frank> i think you need to tank to frank...|
|                                                          |  #frank_talk:frank> frank frank frank                   |
|                                                          |  *** User me joined room #frank_talk                    |
+----------------------------------------------------------+---------------------------------------------------------|

```


