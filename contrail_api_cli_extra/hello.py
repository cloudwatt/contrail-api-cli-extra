from contrail_api_cli.commands import Arg, Command


class Hello(Command):
    description = 'Greeting command'
    who = Arg(nargs='?', default='cli')

    def __call__(self, who=None):
        print 'Hello %s !' % who
