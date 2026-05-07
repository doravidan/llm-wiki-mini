from __future__ import annotations
import argparse
from .core import init_wiki, ingest_file, ask

def main(argv=None):
    p=argparse.ArgumentParser(prog='llm-wiki-mini'); sub=p.add_subparsers(dest='cmd', required=True)
    i=sub.add_parser('init'); i.add_argument('wiki')
    ing=sub.add_parser('ingest'); ing.add_argument('wiki'); ing.add_argument('source'); ing.add_argument('--title')
    a=sub.add_parser('ask'); a.add_argument('wiki'); a.add_argument('query')
    args=p.parse_args(argv)
    if args.cmd=='init': print(init_wiki(args.wiki))
    elif args.cmd=='ingest': print(ingest_file(args.wiki,args.source,args.title))
    elif args.cmd=='ask': print(ask(args.wiki,args.query))
if __name__=='__main__': main()
