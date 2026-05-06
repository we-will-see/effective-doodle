from core.utils.fingerprint import content_hash, idempotency_fingerprint


def test_content_hash_is_stable() -> None:
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abcd")


def test_idempotency_fingerprint_is_stable_and_namespaced() -> None:
    fp1 = idempotency_fingerprint("bse_filing", "123", "deadbeef")
    fp2 = idempotency_fingerprint("bse_filing", "123", "deadbeef")
    fp3 = idempotency_fingerprint("bse_filing", "124", "deadbeef")
    assert fp1 == fp2
    assert fp1 != fp3

