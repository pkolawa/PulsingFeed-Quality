-- ============================================================
-- PulsingFeed Quality — Publishers Seed
-- Źródło prawdy: shared/publishers.json (katalog główny projektu)
-- Ten plik należy aktualizować razem z shared/publishers.json
-- ============================================================

INSERT INTO publishers (name, rss_url, website_url) VALUES
  ('TVN24',                              'https://tvn24.pl/najnowsze.xml',                             'https://tvn24.pl'),
  ('Rzeczpospolita',                     'https://www.rp.pl/rss/1',                                    'https://www.rp.pl'),
  ('Wiadomości Gazeta.pl',               'https://wiadomosci.gazeta.pl/pub/rss/wiadomosci.xml',        'https://wiadomosci.gazeta.pl'),
  ('Spider''s Web (Lifestyle i technologia)', 'https://spidersweb.pl/feed',                            'https://spidersweb.pl'),
  ('Interia (Wydarzenia)',               'https://fakty.interia.pl/feed',                              'https://interia.pl'),
  ('Bankier.pl (Giełda i finanse)',      'https://www.bankier.pl/rss/wiadomosci.xml',                  'https://www.bankier.pl'),
  ('Antyweb (Nowe technologie)',         'https://antyweb.pl/feed',                                    'https://antyweb.pl'),
  ('BBC News (World)',                   'https://feeds.bbci.co.uk/news/world/rss.xml',                'https://www.bbc.com/news/world'),
  ('The New York Times (Strona główna)','https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',   'https://www.nytimes.com'),
  ('The Guardian (Wydarzenia)',          'https://www.theguardian.com/world/rss',                      'https://www.theguardian.com'),
  ('TechCrunch (Startup i IT)',          'https://techcrunch.com/feed/',                               'https://techcrunch.com'),
  ('Wired (Nauka i kultura cyfrowa)',    'https://www.wired.com/feed/rss',                             'https://www.wired.com'),
  ('The Verge (Recenzje i technologie)','https://www.theverge.com/rss/index.xml',                      'https://www.theverge.com'),
  ('Al Jazeera (Wiadomości ogólne)',     'https://www.aljazeera.com/xml/rss/all.xml',                  'https://www.aljazeera.com'),
  ('BBC News',                           'https://feeds.bbci.co.uk/news/rss.xml',                      'https://www.bbc.com/news'),
  ('CNN International',                  'http://rss.cnn.com/rss/edition.rss',                         'https://edition.cnn.com'),
  ('The Washington Post (World)',        'https://feeds.washingtonpost.com/rss/world',                  'https://www.washingtonpost.com'),
  ('MIT News (AI)',                      'http://news.mit.edu/rss/topic/artificial-intelligence2',      'https://news.mit.edu'),
  ('Onet Wiadomości',                    'https://wiadomosci.onet.pl/.feed',                           'https://wiadomosci.onet.pl'),
  ('Polsat News',                        'https://www.polsatnews.pl/rss/wszystkie.xml',                 'https://www.polsatnews.pl'),
  ('Wirtualne Media',                    'https://www.wirtualnemedia.pl/rss/aktualnosci',               'https://www.wirtualnemedia.pl'),
  ('RMF24',                              'http://rmf24.pl/feed',                                        'https://www.rmf24.pl')
ON CONFLICT (rss_url) DO NOTHING;
