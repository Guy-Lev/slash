import itertools

from collections import OrderedDict

from orderedset import OrderedSet

from ...exceptions import UnknownFixtures, InvalidFixtureScope, CyclicFixtureDependency

from .namespace import Namespace
from .parameters import iter_parametrization_fixtures
from .fixture_base import FixtureBase
from .utils import get_real_fixture_name_from_argument


_fixture_id = itertools.count()



class Fixture(FixtureBase):

    def __init__(self, store, fixture_func):
        super(Fixture, self).__init__()
        self.fixture_func = fixture_func
        self.info = self.fixture_func.__slash_fixture__
        self.scope = self.info.scope
        self.namespace = Namespace(store, store.get_current_namespace())

    def __repr__(self):
        return '<Function Fixture around {0}>'.format(self.fixture_func)

    def get_value(self, kwargs, active_fixture):
        if self.info.needs_this:
            assert 'this' not in kwargs
            kwargs['this'] = active_fixture
        return self.fixture_func(**kwargs)

    def _resolve(self, store):
        assert self.fixture_kwargs is None

        assert self.parametrization_ids is None
        self.parametrization_ids = OrderedSet()

        kwargs = OrderedDict()
        parametrized = set()

        for name, param in iter_parametrization_fixtures(self.fixture_func):
            store.register_fixture_id(param)
            parametrized.add(name)
            self.parametrization_ids.add(param.info.id)

        for param_name, arg in self.info.required_args.items():
            if param_name in parametrized:
                continue
            try:
                needed_fixture = self.namespace.get_fixture_by_name(get_real_fixture_name_from_argument(arg))

                if needed_fixture.scope < self.scope:
                    raise InvalidFixtureScope('Fixture {0} is dependent on {1}, which has a smaller scope ({2} > {3})'.format(
                        self.info.name, param_name, self.scope, needed_fixture.scope))

                if needed_fixture is self:
                    raise CyclicFixtureDependency('Cyclic fixture dependency detected in {0}: {1} depends on itself'.format(
                        self.info.func.__code__.co_filename,
                        self.info.name))
                kwargs[param_name] = needed_fixture.info.id
            except LookupError:
                raise UnknownFixtures(param_name)
        return kwargs

