#!/usr/bin/env python
'''
bog simple markov
module use:
    instantiate a Markov()
    use slurpfile, slurpstring to feed
    use markov, vokram, markov2 for output
command line example:
    run marko.py -h
'''

import os, re, sqlite3

class Sqlite(object):

    def __init__(self, name):
        '''
        sqlite database
        '''
        init = False
        if not os.path.exists(name):
            init = True
        self.conn = sqlite3.connect(name)
        self.cur = self.conn.cursor()
        if init:
            self.cur.execute('''
            CREATE table pairs (
            prev TEXT,
            next TEXT,
            count INTEGER,
            PRIMARY KEY (prev, next)
            )
            ''')
            self.conn.commit()

    def pair(self, word1, word2):
        self.cur.execute('''
        SELECT prev, next from pairs
        WHERE prev=? AND next=?
        ORDER BY RANDOM() * count
        LIMIT 1
        ''', (word1, word2))
        return self.cur.fetchone()

    def prev(self, word):
        self.cur.execute('''
        SELECT prev, next from pairs
        WHERE next = ?
        ORDER BY RANDOM() * count
        LIMIT 1
        ''', (word,))
        return self.cur.fetchone()

    def next(self, word):
        self.cur.execute('''
        SELECT prev, next from pairs
        WHERE prev = ?
        ORDER BY RANDOM() * count
        LIMIT 1
        ''', (word,))
        return self.cur.fetchone()

    def rand(self):
        self.cur.execute('''
        SELECT prev, next from pairs
        ORDER BY RANDOM() * count
        LIMIT 1
        ''')
        return self.cur.fetchone()

    def insert(self, pair):
        self.cur.execute('''
        INSERT OR REPLACE INTO pairs
        VALUES (?, ?, COALESCE(
        (SELECT count FROM pairs WHERE prev=? AND next=?), 0) + 1)
        ''', (pair[0], pair[1], pair[0], pair[1]))

    def commit(self):
        self.conn.commit()

class Markov(object):
    '''
    base markov class
    '''

    def __init__(self, db, name):
        '''
        only sqlite supported at the moment
        '''
        if db == 'sqlite':
            self.db = Sqlite(name)
        else:
            raise Exception('%s not supported' % db)

    def vokram(self, phrase):
        '''
        chain ending in phrase
        '''
        def _vokram(word1=None, word2=None):
            y = None
            if word2:
                y = self.db.pair(word1, word2)
            if not y and word2:
                y = self.db.prev(word2)
            if not y and word1:
                y = self.db.prev(word1)
            if not y:
                y = self.db.rand()

            yield y[1]
            if y and y[0] is not None:
                yield y[0]
            while y and y[0] is not None:
                y = self.db.prev(y[0])
                if y and y[0] is not None:
                    yield y[0]

        word1, word2 = self._words(phrase)
        res = [i for i in _vokram(word1, word2) if i is not None]
        res.reverse()
        return (' '.join(res)).strip()

    def markov(self, phrase):
        '''
        chain starting with phrase
        '''
        def _markov(word1=None, word2=None):
            y = None
            if word2:
                y = self.db.pair(word1, word2)
            if not y and word1:
                y = self.db.next(word1)
            if not y and word2:
                y = self.db.next(word2)
            if not y:
                y = self.db.rand()

            yield y[0]
            while y[1] is not None:
                y = self.db.next(y[1])
                yield y[0]

        word1, word2 = self._words(phrase)
        res = [i for i in _markov(word1, word2) if i is not None]
        return (' '.join(res)).strip()

    def markov2(self, phrase):
        '''
        chain containing phrase
        '''
        p = self.vokram(phrase)
        n = self.markov(phrase)
        w = ' '.join([i for i in self._words(phrase) if i is not None])
        if w and p.endswith(w) and n.startswith(w):
            p = p.replace(' %s' % w, '')
        return '%s %s' % (p, n)

    def slurpfile(self, file):
        '''
        feed the engine a file
        '''
        fh = open(file)
        for line in fh.readlines():
            if not line.strip():
                continue
            for i in self._parse('%s' % line, line[0] == line[0].upper()):
                self.db.insert(i)
        self.db.commit()

    def slurpstring(self, string):
        '''
        feed the engine a string
        '''
        for i in self._parse('%s' % string):
            self.db.insert(i)
        self.db.commit()

    def _words(self, string):
        w = string.split(' ')
        word1 = w[0:1] and w[0] or None
        word2 = w[1:2] and w[1] or None
        return word1, word2

    def _parse(self, text, first=True):
        '''
        set first to False if the first word isn't the beginning of a sentence
        '''
        # sanitize
        text = re.sub('[^A-Za-z\. -]', '', text)
        text = re.sub('\.+', '.', text)
        text = re.sub(' +', ' ', text)
        text = text.strip().split(' ')

        if len(text) < 2:
            return
        if first:
            yield (None, text[0].replace('.', ''))
        for i, j in enumerate(text[:-1]):
            if text[i+1].endswith('.'):
                yield (j, text[i+1][:-1])
                yield (text[i+1][:-1], None)
            elif j.endswith('.'):
                yield (None, text[i+1])
            else:
                yield (j, text[i+1])
        if len(text) > 1:
            yield (text[i+1], None)

if __name__ == '__main__':
    from optparse import OptionParser
    import sys

    parser = OptionParser()
    parser.add_option('-d', '--db', default='marko.db',
                      help='db name. default is "marko.db"')
    parser.add_option('-f', '--file', help='feed file')
    parser.add_option('-s', '--string', action='store_true',
                      help='feed string')
    parser.add_option('-m', '--markov2', action='store_true',
                      help='markov2')
    parser.add_option('-v', '--vokram', action='store_true',
                      help='vokram')
    opts, args = parser.parse_args()

    word1 = args[0:1] and args[0] or None
    word2 = args[1:2] and args[1] or None

    m = Markov('sqlite', opts.db)

    if opts.file:
        m.slurpfile(opts.file)
    elif opts.string:
        m.slurpstring(' '.join(args))
    elif opts.markov2:
        print m.markov2(' '.join(args))
    elif opts.vokram:
        print m.vokram(' '.join(args))
    else:
        print m.markov(' '.join(args))
