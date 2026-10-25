"""Local Playwright regression tests; no database or external ATS required."""
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from playwright.async_api import async_playwright
from app.services import browser_service as service


@pytest.mark.skipif(os.getenv("RUN_BROWSER_TESTS") != "1", reason="Set RUN_BROWSER_TESTS=1 on a host permitting Chromium launch")
def test_browser_workflow():
    async def run():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            browser_context = await browser.new_context()
            page = await browser_context.new_page()
            session = service.BrowserSession(pw, browser, page)
            service._sessions[-2] = session
            try:
                latest = await page.context.new_page()
                await latest.set_content('''<input type="email" aria-label="Newsletter">
                    <iframe srcdoc='<label>First name<input name="first_name"></label>
                    <label>Email<input type="email" name="email"></label>
                    <label>Gender<input name="gender"></label>
                    <label>Electronic signature<input name="signature"></label>
                    <input type="file" name="resume" style="display:none">
                    <button onclick="window.submitted=true">Apply</button>'></iframe>''')
                frame = latest.frames[1]
                await frame.locator('[name="first_name"]').wait_for()
                assert await service.get_active_page(-2) == latest
                assert await service.get_form_context(latest) == frame
                profile = SimpleNamespace(first_name="Test", last_name="Applicant", email="test@example.invalid",
                                          phone=None, linkedin_url=None, github_url=None, portfolio_url=None)
                result = await service.autofill_application_form(-2, profile, b'%PDF-fixture', 'chosen.pdf')
                assert result['filled_fields'] == ['first_name', 'email']
                assert result['resume_uploaded'] and result['manual_review_required']
                assert await frame.locator('[name="first_name"]').input_value() == 'Test'
                assert await latest.locator('input').input_value() == ''
                for name in ('gender', 'signature'):
                    assert await frame.locator(f'[name="{name}"]').input_value() == ''
                assert await frame.locator('[name="resume"]').evaluate('el => el.files[0].name') == 'chosen.pdf'
                await service.resolve_application_page(-2)
                assert not await frame.evaluate('Boolean(window.submitted)')
                await latest.close()
                assert await service.get_active_page(-2) == page
                assert not (await service.autofill_application_form(-2, profile))['resume_uploaded']
                await browser.close()
                try:
                    await service.get_active_page(-2)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Expected closed-browser error')
            finally:
                service._sessions.pop(-2, None)
                await browser.close()
    asyncio.run(run())


@pytest.mark.skipif(os.getenv("RUN_BROWSER_TESTS") != "1", reason="Set RUN_BROWSER_TESTS=1 on a host permitting Chromium launch")
def test_delayed_form_and_upload_safety():
    async def run():
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            browser_context = await browser.new_context()
            page = await browser_context.new_page()
            try:
                await page.set_content('''<script>setTimeout(() => {
                    const frame = document.createElement('iframe');
                    frame.srcdoc = '<input type="file" name="resume"><input type="file" name="cover_letter">';
                    document.body.append(frame);
                }, 150)</script>''')
                context = await service.get_form_context(page)
                assert context != page
                assert await service.upload_resume_file(context, b'pdf', 'resume.pdf')
                await page.set_content('<input type="file"><input type="file">')
                assert not await service.upload_resume_file(page, b'pdf', 'resume.pdf')
                await page.set_content('<input type="file" name="cover_letter">')
                assert not await service.upload_resume_file(page, b'pdf', 'resume.pdf')
                await page.set_content('<label>First name<input></label><label>First name<input></label>')
                assert not await service.fill_first(page, [page.get_by_label('First name')], 'Test')
            finally:
                await browser.close()
    asyncio.run(run())


def test_missing_session():
    async def run():
        try:
            await service.get_active_page(-1)
        except RuntimeError as exc:
            assert 'not open' in str(exc)
        else:
            raise AssertionError('Expected missing session error')
    asyncio.run(run())


def test_active_page_and_frame_selection():
    async def run():
        def make_page(url, focused=False):
            return SimpleNamespace(url=url, is_closed=lambda: False,
                evaluate=AsyncMock(return_value=focused), bring_to_front=AsyncMock())
        older, newer = make_page('https://example.invalid/old'), make_page('https://example.invalid/new')
        session = SimpleNamespace(browser=SimpleNamespace(is_connected=lambda: True),
                                  context=SimpleNamespace(pages=[older, newer]), page=older)
        with patch.dict(service._sessions, {-3: session}):
            assert await service.get_active_page(-3) == newer
            older.evaluate.return_value = True
            assert await service.get_active_page(-3) == older
            assert session.page == older
        frame = SimpleNamespace(url='https://ats.invalid/form', locator=lambda _: SimpleNamespace(count=AsyncMock(return_value=1)))
        main = SimpleNamespace(url='https://company.invalid', main_frame=object(), frames=[frame],
                               locator=lambda _: SimpleNamespace(count=AsyncMock(return_value=0)))
        assert await service.get_form_context(main) == frame
    asyncio.run(run())


def test_autofill_endpoint_selected_resume_and_commit():
    from app.routers.applications import autofill_application
    async def run():
        application = SimpleNamespace(id=7, resume_version_id=42, application_url='https://old.invalid', status='preparing')
        profile = object()
        resume = SimpleNamespace(content='selected resume', status='approved', version=3)
        db = SimpleNamespace(get=AsyncMock(side_effect=[application, resume]),
            execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: profile))),
            commit=AsyncMock(), refresh=AsyncMock())
        result = dict(status='ready_for_review', url='https://ats.invalid/form', filled_fields=['email'],
                      skipped_fields=[], resume_uploaded=True, manual_review_required=True)
        with patch('app.routers.applications.build_resume_pdf', return_value=b'%PDF-test') as pdf, \
             patch('app.routers.applications.autofill_application_form', new=AsyncMock(return_value=result)) as fill:
            response = await autofill_application(7, db)
            assert db.get.call_args_list[1].args[1] == 42
            pdf.assert_called_once_with('selected resume')
            assert fill.call_args.kwargs['resume_bytes'] == b'%PDF-test'
            assert fill.call_args.kwargs['profile'] is profile
            assert response['application_id'] == 7
            assert application.application_url == result['url']
            assert application.status == 'ready_for_review'
            db.commit.assert_awaited_once()
    asyncio.run(run())


def test_autofill_endpoint_rejects_unapproved_resume():
    from fastapi import HTTPException
    from app.routers.applications import autofill_application
    async def run():
        db = SimpleNamespace(get=AsyncMock(side_effect=[SimpleNamespace(resume_version_id=42), SimpleNamespace(status='draft')]),
            execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: object()))))
        with patch('app.routers.applications.autofill_application_form', new=AsyncMock()) as fill:
            with pytest.raises(HTTPException) as exc:
                await autofill_application(7, db)
            assert exc.value.status_code == 400
            fill.assert_not_awaited()
    asyncio.run(run())
