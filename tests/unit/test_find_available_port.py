import socket
from unittest.mock import MagicMock, patch

from super_dev.cli import SuperDevCLI
from super_dev.web.api import find_available_port


def test_find_available_port_free():
    """测试端口未被占用时直接返回起始端口。"""
    port = find_available_port("127.0.0.1", start_port=17890)
    assert port == 17890


def test_find_available_port_occupied_auto_increment():
    """测试端口被占用时自动递增到下一个可用端口。"""
    test_port = 17891
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", test_port))
    s.listen(1)

    try:
        available = find_available_port("127.0.0.1", start_port=test_port)
        assert available == test_port + 1
    finally:
        s.close()


def test_cli_parser_web_default_port():
    """测试 CLI web 命令默认端口为 7890。"""
    cli = SuperDevCLI()
    parser = cli._create_parser()
    args = parser.parse_args(["web"])
    assert args.port == 7890
    assert args.host == "127.0.0.1"


def test_cli_cmd_web_port_conflict_message():
    """测试 CLI _cmd_web 在端口冲突时打印切换提示并传递可用端口给 uvicorn。"""
    cli = SuperDevCLI()
    args = MagicMock()
    args.host = "127.0.0.1"
    args.port = 7890

    # 模拟 7890 被占用，可用端口返回 7891
    with patch("super_dev.web.api.find_available_port", return_value=7891):
        with patch("uvicorn.run") as mock_run:
            result = cli._cmd_web(args)
            assert result == 0
            mock_run.assert_called_once_with(
                "super_dev.web.api:app", host="127.0.0.1", port=7891, log_level="info"
            )
