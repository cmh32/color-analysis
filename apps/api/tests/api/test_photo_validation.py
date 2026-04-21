from color_analysis.api.photos import _is_safe_filename


def test_is_safe_filename_allows_simple_name() -> None:
    assert _is_safe_filename("portrait_01.jpg") is True


def test_is_safe_filename_rejects_path_like_name() -> None:
    assert _is_safe_filename("../portrait.jpg") is False
    assert _is_safe_filename("folder\\portrait.jpg") is False


def test_is_safe_filename_rejects_control_characters() -> None:
    assert _is_safe_filename("portrait\u0000.jpg") is False
