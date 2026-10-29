"""Scoped CLI adapter: an explicit setting must not play a shutdown animation on exit."""
import sys


def read_only_args(args):
    from g515_adapter import READ_KEYS
    if len(args)!=3 or args[0]!='config' or not args[1] or args[2] not in READ_KEYS:
        raise ValueError('Read-only Solaar requires exactly one allowlisted setting and no value')
    return args


def guard_reads(settings,rgb_power):
    """No settings writes/apply, RGB controller start, or shutdown animation."""
    def denied(*args,**kwargs):raise RuntimeError('Hardware writes are disabled in read-only Solaar')
    pending=[settings.Setting];seen=set()
    while pending:
        cls=pending.pop()
        if cls in seen:continue
        seen.add(cls);pending.extend(cls.__subclasses__())
        for name in ('write','write_key_value','write_item_value','apply'):
            if hasattr(cls,name):setattr(cls,name,denied)
    for name in ('FeatureRW','FeatureRWMap','RegisterRW'):
        cls=getattr(settings,name,None)
        if cls is not None and hasattr(cls,'write'):cls.write=denied
    if rgb_power is not None:
        rgb_power.start=denied
        rgb_power.cleanup=lambda device:rgb_power.stop(device)


def main(args=None):
    args=list(sys.argv[1:] if args is None else args)
    readonly=args[:1]==['--read-only']
    if readonly:args=read_only_args(args[1:])  # validate before importing device code
    # Stock and patched Solaar builds with the same release number can differ.
    # An optional RGB power manager must not be a prerequisite for reading.
    try:from logitech_receiver import rgb_power
    except ImportError:rgb_power=None
    # Process-local only: never play a firmware shutdown animation on close.
    if rgb_power is not None:rgb_power.cleanup=lambda device:rgb_power.stop(device)
    if readonly:
        from logitech_receiver import settings,settings_templates  # load overrides before guarding
        guard_reads(settings,rgb_power)
        from solaar.cli import run
        return run(args)
    from solaar.gtk import main as cli_main
    return cli_main()


if __name__=='__main__':sys.exit(main())
