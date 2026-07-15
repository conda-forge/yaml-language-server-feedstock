"""Smoke test whether the server starts and reports an expected diagnostic."""

from __future__ import annotations

import asyncio
from typing import Any
import lsprotocol.types as lsp
import pytest
from pytest_lsp import ClientServerConfig, LanguageClient, client_capabilities
from pytest_lsp import fixture as pylsp_fixture


YLS_CMD = ["yaml-language-server", "--stdio"]
WS_URI = "file:///path/to/test"
BAD_URI = f"{WS_URI}/bad.yaml"
BAD_YAML = "foo: *undefined_anchor"


@pylsp_fixture(config=ClientServerConfig(server_command=YLS_CMD))
async def client(lsp_client: LanguageClient):
    """Provide a configured client and server."""
    # Avoid pygls.exceptions.JsonRpcMethodNotFound for unhandled message types
    [
        lsp_client.feature(no_op)(lambda _params: None)
        for no_op in [lsp.CLIENT_REGISTER_CAPABILITY, lsp.TELEMETRY_EVENT]
    ]

    caps = client_capabilities("visual-studio-code")
    folder = lsp.WorkspaceFolder(uri=WS_URI, name="project")
    init_params = lsp.InitializeParams(caps, workspace_folders=[folder])
    await lsp_client.initialize_session(init_params)

    yield

    await lsp_client.shutdown_session()


@pytest.mark.asyncio
async def test_diagnostics(client: LanguageClient):
    """Verify diagnostics are reported."""
    td = lsp.TextDocumentItem(uri=BAD_URI, language_id="yaml", version=1, text=BAD_YAML)
    client.text_document_did_open(lsp.DidOpenTextDocumentParams(text_document=td))
    diag_task = client.wait_for_notification(lsp.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
    await asyncio.wait_for(diag_task, 30)
    diags = client.diagnostics
    assert "*undefined_anchor" in diags[BAD_URI][0].message
