#!/usr/bin/env python2
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

ignores = ['markov', 'markov2', 'vokram']

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
            CREATE table triples (
            first TEXT,
            middle TEXT,
            last TEXT,
            count INTEGER,
            PRIMARY KEY (first, middle, last)
            )
            ''')
            self.conn.commit()

    def next(self, word1, word2):
        self.cur.execute('''
        SELECT first, middle, last from triples
        WHERE first=? AND middle=?
        ORDER BY RANDOM() * count
        LIMIT 1
        ''', (word1, word2))
        return self.cur.fetchone()

    def prev(self, word1, word2):
        self.cur.execute('''
        SELECT first, middle, last from triples
        WHERE middle=? AND last=?
        ORDER BY RANDOM() * count
        LIMIT 1
        ''', (word1, word2))
        return self.cur.fetchone()

    def onext(self, word):
        self.cur.execute('''
        SELECT first, middle, last from triples
        WHERE first = ?
        ORDER BY RANDOM() * count
        LIMIT 1
        ''', (word,))
        return self.cur.fetchone()

    def oprev(self, word):
        self.cur.execute('''
        SELECT first, middle, last from triples
        WHERE last = ?
        ORDER BY RANDOM() * count
        LIMIT 1
        ''', (word,))
        return self.cur.fetchone()

    def omid(self, word):
        self.cur.execute('''
        SELECT first, middle, last from triples
        WHERE middle = ?
        ORDER BY RANDOM() * count
        LIMIT 1
        ''', (word,))
        return self.cur.fetchone()

    def rand(self):
        self.cur.execute('''
        SELECT first, middle, last from triples
        ORDER BY RANDOM() * count
        LIMIT 1
        ''')
        return self.cur.fetchone()

    def insert(self, triple):
        self.cur.execute('''
        INSERT OR REPLACE INTO triples
        VALUES (?, ?, ?, COALESCE(
        (SELECT count FROM triples WHERE first=? AND middle=? AND last=?), 0) + 1)
        ''', (triple[0], triple[1], triple[2], triple[0], triple[1], triple[2]))

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
                y = self.db.prev(word1, word2)
            if not y and word2:
                y = self.db.oprev(word2)
                if not y:
                    y = self.db.omid(word2)
            if not y and word1:
                y = self.db.oprev(word1)
                if not y:
                    y = self.db.omid(word1)
            if not y:
                y = self.db.rand()

            yield y[2]
            yield y[1]
            if y[0] is not None:
                yield y[0]
            while y and y[0] is not None:
                y = self.db.prev(y[0], y[1])
                if y and y[0] is not None:
                    yield y[0]

        word1, word2 = self._words(phrase)
        res = [i for i in _vokram(word1, word2) if i is not None]
        res.reverse()
        if res:
            return (' '.join(res)).strip()
        return ''

    def markov(self, phrase):
        '''
        chain starting with phrase
        '''
        def _markov(word1=None, word2=None):
            y = None
            if word2:
                y = self.db.next(word1, word2)
            if not y and word1:
                y = self.db.onext(word1)
                if not y:
                    y = self.db.omid(word1)
            if not y and word2:
                y = self.db.onext(word2)
                if not y:
                    y = self.db.omid(word2)
            if not y:
                y = self.db.rand()
            if not y:
                return

            yield y[0]
            yield y[1]
            while y[2] is not None:
                y = self.db.next(y[1], y[2])
                if not y:
                    return
                yield y[2]

        word1, word2 = self._words(phrase)
        res = [i for i in _markov(word1, word2) if i is not None]
        if res:
            return (' '.join(res)).strip()
        return ''

    def markov2(self, phrase):
        '''
        chain containing phrase
        '''
        p = self.vokram(phrase)
        n = self.markov(phrase)
        word1, word2 = self._words(phrase)
        w = ' '.join([i for i in [word1, word2] if i is not None])
        if w and p.endswith(w) and n.startswith(w):
            p = p.replace(' %s' % w, '')
        elif word1 and p.endswith(word1) and n.startswith(word1):
            p = p.replace(' %s' % word1, '')
        elif word2 and p.endswith(word2) and n.startswith(word2):
            p = p.replace(' %s' % word2, '')
        return '%s %s' % (p, n)

    def slurpfile(self, file):
        '''
        feed the engine a file
        '''
        fh = open(file)
        lastwords = []
        for line in fh.readlines():
            line = line.strip()
            if not line:
                continue
            f = line[0] == line[0].upper()
            l = line.endswith('.')
            if len(lastwords) == 2:
                for i in self._parse('%s %s %s' % (lastwords[0], lastwords[1],
                                                   line.strip().split(' ')[0]),
                                                   False, False):
                    self.db.insert(i)
                lastwords = []
            for i in self._parse(line, f, l):
                self.db.insert(i)
            if not l:
                lastwords.append(line.strip().split(' ')[-1])
        self.db.commit()

    def slurpstring(self, string):
        '''
        feed the engine a string
        '''
        for i in self._parse(string):
            self.db.insert(i)
        self.db.commit()

    def _words(self, string):
        w = string.split(' ')
        word1 = w[0:1] and w[0] or None
        word2 = w[1:2] and w[1] or None
        return word1, word2

    def _parse(self, text, first=True, last=True):
        '''
        set first to False if the first word isn't the beginning of a sentence
        '''
        # sanitize
        text = re.sub('\?', '.', text)
        text = re.sub('\!', '.', text)
        text = re.sub('[^A-Za-z0-9\. -]', '', text)
        text = re.sub('\.+', '.', text)
        text = re.sub(' +', ' ', text)
        text = text.strip().split('.')

        if first and text and text[0] in ignores:
            return

        text = [[None] + i.strip().split(' ') + [None] for i in text if i]
        if text and not first:
            text[0] = text[0][1:]
        if text and not last:
            text[-1] = text[-1][:-1]

        for sentence in text:
            for i, j in enumerate(sentence[:-2]):
                yield (j, sentence[i+1], sentence[i+2])

if __name__ == '__main__':
    from optparse import OptionParser
    import readline, sys

    usage = '%prog [-d db] [-f file] [-h] [-i] [-m] [-s string] [-v] [words]'
    dbdefault = '%s/marko.db' % os.path.dirname(os.path.realpath(__file__))
    parser = OptionParser(usage=usage)
    parser.add_option('-d', '--db', default=dbdefault,
                      help='db name. default is %s' % dbdefault)
    parser.add_option('-f', '--file', help='feed file')
    parser.add_option('-i', '--interactive', action='store_true',
                      help='repl')
    parser.add_option('-s', '--string', action='store_true',
                      help='feed string')
    parser.add_option('-m', '--markov2', action='store_true',
                      help='markov2')
    parser.add_option('-v', '--vokram', action='store_true',
                      help='vokram')
    opts, args = parser.parse_args()
    args = ' '.join(args)

    m = Markov('sqlite', opts.db)

    if opts.file:
        m.slurpfile(opts.file)
    elif opts.string:
        m.slurpstring(args)
    else:
        if opts.markov2:
            cmd = m.markov2
        elif opts.vokram:
            cmd = m.vokram
        else:
            cmd = m.markov
        print cmd(args)
        while opts.interactive:
            args = raw_input('> ')
            if not args:
                break
            print cmd(args)
