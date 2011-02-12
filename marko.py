#!/usr/bin/env python
''' bog simple markov '''

import os, re, sqlite3

class Sqlite(object):

    m0 = '''
    SELECT * from pairs
    ORDER BY RANDOM()
    LIMIT 1
    '''
    m1 = '''
    SELECT * from pairs
    WHERE prev = ?
    ORDER BY RANDOM()
    LIMIT 1
    '''
    m2 = '''
    SELECT * from pairs
    WHERE prev=? AND next=?
    ORDER BY RANDOM()
    LIMIT 1
    '''
    v1 = '''
    SELECT * from pairs
    WHERE next = ?
    ORDER BY RANDOM()
    LIMIT 1
    '''
    ins = 'INSERT INTO pairs VALUES (?,?)'

    def __init__(self, name):
        init = False
        if not os.path.exists(name):
            init = True
        self.conn = sqlite3.connect(name)
        self.cur = self.conn.cursor()
        if init:
            print 'creating %s' % name
            self.cur.execute('CREATE table pairs (prev text, next text)')
            self.conn.commit()

class Markov(object):

    def __init__(self, db, name):
        if db == 'sqlite':
            d = Sqlite(name)
            self.conn = d.conn
            self.cur = d.cur
            self.m0 = d.m0
            self.m1 = d.m1
            self.m2 = d.m2
            self.v1 = d.v1
            self.ins = d.ins
        else:
            print '%s not supported'

    def _words(self, string):
        w = string.split(' ')
        word1 = w[0:1] and w[0] or None
        word2 = w[1:2] and w[1] or None
        return word1, word2

    def vokram(self, phrase):
        def _vokram(word1=None, word2=None):
            if word2:
                self.cur.execute(self.m2, (word1, word2))
            elif word1:
                self.cur.execute(self.v1, (word1,))
            else:
                self.cur.execute(self.m0)
            y = self.cur.fetchone()

            if not y and word1:
                self.cur.execute(self.v1, (word1,))
                y = self.cur.fetchone()
            if not y and word2:
                self.cur.execute(self.v1, (word2,))
                y = self.cur.fetchone()
            if not y:
                self.cur.execute(self.m0)
                y = self.cur.fetchone()

            yield y[1]
            if y and y[0] is not None:
                yield y[0]
            while y and y[0] is not None:
                self.cur.execute(self.v1, (y[0],))
                y = self.cur.fetchone()
                if y[0] is not None:
                    yield y[0]

        word1, word2 = self._words(phrase)
        res = [i for i in _vokram(word1, word2) if i is not None]
        res.reverse()
        return (' '.join(res)).strip()

    def markov(self, phrase):
        def _markov(word1=None, word2=None):
            if word2:
                self.cur.execute(self.m2, (word1, word2))
            elif word1:
                self.cur.execute(self.m1, (word1,))
            else:
                self.cur.execute(self.m0)
            y = self.cur.fetchone()

            if not y and word1:
                self.cur.execute(self.m1, (word1,))
                y = self.cur.fetchone()
            if not y and word2:
                self.cur.execute(self.m1, (word2,))
                y = self.cur.fetchone()
            if not y:
                self.cur.execute(self.m0)
                y = self.cur.fetchone()

            yield y[0]
            while y[1] is not None:
                self.cur.execute(self.m1, (y[1],))
                y = self.cur.fetchone()
                yield y[0]

        word1, word2 = self._words(phrase)
        res = [i for i in _markov(word1, word2) if i is not None]
        return (' '.join(res)).strip()

    def markov2(self, phrase):
        word1, word2 = self._words(phrase)
        p = self.vokram(phrase)
        n = self.markov(phrase)
        w = ' '.join([i for i in [word1, word2] if i is not None])
        if p.endswith(w) and n.startswith(w):
            p = p.replace(' %s' % w, '')
        elif word1 and p.endswith(word1) and n.startswith(word1):
            p = p.replace(' %s' % word1, '')
        elif word2 and p.endswith(word2) and n.startswith(word2):
            p = p.replace(' %s' % word2, '')
        return '%s %s' % (p, n)

    def slurpfile(self, file):
        fh = open(file)
        for line in fh.readlines():
            if not line.strip():
                continue
            for i in self._parse('%s' % line, line[0] == line[0].upper()):
                self.cur.execute(self.ins, i)
        self.conn.commit()

    def slurpstring(self, string):
        for i in self._parse('%s' % string):
            self.cur.execute(self.ins, i)
        self.conn.commit()

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

    m = Markov('sqlite', 'marko.db')

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
