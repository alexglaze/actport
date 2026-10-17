import pytest

from airlock.scope import (
    Scope,
    command_allowed,
    host_allowed,
    normalize_path,
    parse_amount,
    parse_command,
    parse_recipient,
    path_matches,
    path_within,
    recipient_allowed,
    url_host,
)


class TestPaths:
    def test_relative_paths_resolve_against_cwd(self) -> None:
        assert normalize_path("out/a.md", "/workspace") == "/workspace/out/a.md"

    def test_dot_dot_is_collapsed_before_comparison(self) -> None:
        assert normalize_path("/workspace/out/../src/x.py") == "/workspace/src/x.py"
        assert normalize_path("../../etc/hosts", "/workspace/out") == "/etc/hosts"

    def test_leading_double_slash_is_not_special(self) -> None:
        assert normalize_path("//workspace/out") == "/workspace/out"

    @pytest.mark.parametrize("bad", ["", "a\x00b", None, 3])
    def test_invalid_paths_raise(self, bad: object) -> None:
        with pytest.raises(ValueError):
            normalize_path(bad)  # type: ignore[arg-type]

    def test_within_requires_a_component_boundary(self) -> None:
        assert path_within("/workspace/out/a", "/workspace/out")
        assert path_within("/workspace/out", "/workspace/out/")
        assert not path_within("/workspace/outside/a", "/workspace/out")

    def test_matches_prefixes_and_globs(self) -> None:
        assert (
            path_matches("/workspace/.airlock/policy.toml", ("/workspace/.airlock",)) == "/workspace/.airlock"
        )
        assert path_matches("/home/u/.ssh/id", ("/home/*/.ssh/*",)) == "/home/*/.ssh/*"
        assert path_matches("/workspace/out/a", ("/workspace/src", "*.toml")) is None


class TestHosts:
    @pytest.mark.parametrize(
        ("host", "ok"),
        [
            ("docs.example.org", True),
            ("DOCS.Example.org.", True),
            ("api.docs.example.org", True),
            ("example.org", False),
            ("evildocs.example.org", False),
            ("docs.example.org.attacker.test", False),
            ("d\u043ecs.example.org", False),  # Cyrillic o: an IDN lookalike
        ],
    )
    def test_exact_or_true_subdomain_only(self, host: str, ok: bool) -> None:
        assert host_allowed(host, ("docs.example.org",)) is ok

    def test_url_host_ignores_port_and_case(self) -> None:
        assert url_host("https://Docs.Example.org:8443/a?b=c") == "docs.example.org"

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://docs.example.org/",
            "file:///etc/hosts",
            "https://user@docs.example.org/",
            "https:///nohost",
            7,
        ],
    )
    def test_url_host_rejects_unusable_urls(self, url: object) -> None:
        with pytest.raises(ValueError):
            url_host(url)  # type: ignore[arg-type]


class TestRecipients:
    scope = Scope(recipients=("dana@acme.example",), recipient_domains=("team.example",))

    def test_display_name_form_is_parsed(self) -> None:
        assert parse_recipient("Dana <DANA@Acme.Example>") == ("dana@acme.example", "acme.example")

    @pytest.mark.parametrize(
        "value", ["a@x.example, b@x.example", "a@x.example; b@x.example", "nobody", "@x", 4]
    )
    def test_only_single_addresses_are_accepted(self, value: object) -> None:
        assert not recipient_allowed(value, self.scope)  # type: ignore[arg-type]

    def test_listed_address_or_domain(self) -> None:
        assert recipient_allowed("dana@acme.example", self.scope)
        assert recipient_allowed("anyone@team.example", self.scope)
        assert not recipient_allowed("lee@acme.example", self.scope)


class TestCommandsAndAmounts:
    @pytest.mark.parametrize(
        "cmd", ["pytest -q; make", "pytest && make", "pytest | tee x", "echo $HOME", "a\nb"]
    )
    def test_shell_syntax_is_rejected(self, cmd: str) -> None:
        with pytest.raises(ValueError, match="shell"):
            parse_command(cmd)

    def test_program_must_be_allowlisted(self) -> None:
        scope = Scope(commands=("pytest",))
        assert command_allowed("pytest -q tests/", scope)
        assert not command_allowed("make deploy", scope)
        assert not command_allowed("'unterminated", scope)

    @pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), "ten", True, None])
    def test_amounts_must_be_finite_non_negative_numbers(self, bad: object) -> None:
        with pytest.raises(ValueError):
            parse_amount(bad)

    def test_numeric_strings_are_amounts(self) -> None:
        assert parse_amount("420.50") == 420.5


class TestScopeCeiling:
    ceiling = Scope(
        read_paths=("/workspace",),
        write_paths=("/workspace/out",),
        domains=("example.org",),
        recipient_domains=("acme.example",),
        payees=("Northwind Supplies",),
        commands=("pytest",),
    )

    def test_narrower_scope_is_within_ceiling(self) -> None:
        narrow = Scope(
            read_paths=("/workspace/notes",),
            write_paths=("/workspace/out/reports",),
            domains=("docs.example.org",),
            recipients=("dana@acme.example",),
            payees=("northwind supplies",),
            commands=("pytest",),
        )
        assert narrow.exceeds(self.ceiling) == []

    def test_every_widening_is_reported(self) -> None:
        wide = Scope(
            read_paths=("/etc",),
            write_paths=("/workspace",),
            domains=("other.test",),
            recipients=("x@other.test",),
            recipient_domains=("other.test",),
            payees=("Someone Else",),
            commands=("make",),
        )
        assert len(wide.exceeds(self.ceiling)) == 7
