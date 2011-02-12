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

    mrand = '''
    SELECT * from pairs
    ORDER BY RANDOM()
    LIMIT 1
    '''
    mnext = '''
    SELECT * from pairs
    WHERE prev = ?
    ORDER BY RANDOM()
    LIMIT 1
    '''
    mpair = '''
    SELECT * from pairs
    WHERE prev=? AND next=?
    ORDER BY RANDOM()
    LIMIT 1
    '''
    mprev = '''
    SELECT * from pairs
    WHERE next = ?
    ORDER BY RANDOM()
    LIMIT 1
    '''
    ins = 'INSERT INTO pairs VALUES (?,?)'

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
            print 'creating %s' % name
            self.cur.execute('CREATE table pairs (prev text, next text)')
            self.conn.commit()

class Markov(object):
    '''
    base markov class
    '''

    def __init__(self, db, name):
        '''
        set up db
        '''
        if db == 'sqlite':
            d = Sqlite(name)
            self.conn = d.conn
            self.cur = d.cur
            self.mrand = d.mrand
            self.mnext = d.mnext
            self.mpair = d.mpair
            self.mprev = d.mprev
            self.ins = d.ins
        else:
            raise Exception('%s not supported' % db)

    def vokram(self, phrase):
        '''
        chain ending in phrase
        '''
        def _vokram(word1=None, word2=None):
            if word2:
                self.cur.execute(self.mpair, (word1, word2))
            elif word1:
                self.cur.execute(self.mprev, (word1,))
            else:
                self.cur.execute(self.mrand)
            y = self.cur.fetchone()

            if not y and word1:
                self.cur.execute(self.mprev, (word1,))
                y = self.cur.fetchone()
            if not y and word2:
                self.cur.execute(self.mprev, (word2,))
                y = self.cur.fetchone()
            if not y:
                self.cur.execute(self.mrand)
                y = self.cur.fetchone()

            yield y[1]
            if y and y[0] is not None:
                yield y[0]
            while y[0] is not None:
                self.cur.execute(self.mprev, (y[0],))
                y = self.cur.fetchone()
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
            if word2:
                self.cur.execute(self.mpair, (word1, word2))
            elif word1:
                self.cur.execute(self.mnext, (word1,))
            else:
                self.cur.execute(self.mrand)
            y = self.cur.fetchone()
            if not y and word1:
                self.cur.execute(self.mnext, (word1,))
                y = self.cur.fetchone()
            if not y and word2:
                self.cur.execute(self.mnext, (word2,))
                y = self.cur.fetchone()
            if not y:
                self.cur.execute(self.mrand)
                y = self.cur.fetchone()

            yield y[0]
            while y[1] is not None:
                self.cur.execute(self.mnext, (y[1],))
                y = self.cur.fetchone()
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
                self.cur.execute(self.ins, i)
        self.conn.commit()

    def slurpstring(self, string):
        '''
        feed the engine a string
        '''
        for i in self._parse('%s' % string):
            self.cur.execute(self.ins, i)
        self.conn.commit()

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
