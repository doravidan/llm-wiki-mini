from __future__ import annotations
import argparse, json
from pathlib import Path
from .harness import EvalCase, run_case

REPO = Path('/Users/doravidan/Projects/style-my-look')

def read_rel(rel: str, limit: int = 32000) -> str:
    text = (REPO / rel).read_text(encoding='utf-8', errors='ignore')
    return text[:limit]

def make_cases() -> list[EvalCase]:
    return [
        EvalCase(
            case_id='aitryon_generate_tryon_credit_flow',
            question='Explain the generate-tryon request flow, auth checks, credit charging/refund behavior, rate limiting, and iOS request fields.',
            sources={
                'api-contracts.md': read_rel('shared/api-contracts.md'),
                'generate-tryon-index.ts': read_rel('supabase/functions/generate-tryon/index.ts'),
                'EdgeFunctionClient.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Data/Networking/EdgeFunctionClient.swift'),
                'StudioViewModel.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Studio/StudioViewModel.swift'),
            },
            expected_terms=['generate-tryon','authorization','claims','service','rate','credits','refund','featureType','variationCount','Gemini','resultUrl'],
            expected_sources=['api-contracts.md','generate-tryon-index.ts','EdgeFunctionClient.swift','StudioViewModel.swift'],
            notes='Real AiTryOn backend+iOS flow across API contract, edge function, client, and view model.',
        ),
        EvalCase(
            case_id='aitryon_storekit_receipt_credits',
            question='How does the iOS StoreKit purchase path verify receipts and sync credits with Supabase?',
            sources={
                'EdgeFunctionClient.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Data/Networking/EdgeFunctionClient.swift'),
                'StoreKitManager.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Core/StoreKit/StoreKitManager.swift'),
                'verify-apple-receipt-index.ts': read_rel('supabase/functions/verify-apple-receipt/index.ts'),
                'api-contracts.md': read_rel('shared/api-contracts.md'),
            },
            expected_terms=['StoreKit','receipt','transactionId','originalTransactionId','productId','subscription','credits','verify-apple-receipt','APPLE_SHARED_SECRET','Supabase'],
            expected_sources=['EdgeFunctionClient.swift','StoreKitManager.swift','verify-apple-receipt-index.ts','api-contracts.md'],
            notes='Payment/credits flow: native StoreKit + edge function verification.',
        ),
        EvalCase(
            case_id='aitryon_supabase_migration_checklist',
            question='What is the Supabase migration checklist for AiTryOn, including buckets, Apple sign-in, secrets, edge functions, and iOS config?',
            sources={
                'SUPABASE_MIGRATION_GUIDE.md': read_rel('SUPABASE_MIGRATION_GUIDE.md'),
                'api-contracts.md': read_rel('shared/api-contracts.md'),
                'APIClient.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Data/Networking/APIClient.swift'),
                'CLAUDE.md': read_rel('CLAUDE.md'),
            },
            expected_terms=['Supabase','buckets','models','generations','Apple','com.aitry.on','secrets','GEMINI_API_KEY','PAYPAL_CLIENT_ID','verify-apple-receipt','Config.plist','anon'],
            expected_sources=['SUPABASE_MIGRATION_GUIDE.md','api-contracts.md','APIClient.swift','CLAUDE.md'],
            notes='Ops/doc/code cross-source migration answer.',
        ),
        EvalCase(
            case_id='aitryon_feature_parity_gap_analysis',
            question='What are the remaining feature parity gaps between web and iOS, especially payments, dark mode, deep linking, gallery navigation, and native-only features?',
            sources={
                'feature-parity-checklist.md': read_rel('shared/feature-parity-checklist.md'),
                'PricingView.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Pricing/PricingView.swift'),
                'GalleryView.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Gallery/GalleryView.swift'),
                'MainTabView.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Navigation/MainTabView.swift'),
            },
            expected_terms=['PayPal','Payment','dark','deep','linking','keyboard','swipe','pull','refresh','native','iOS','web'],
            expected_sources=['feature-parity-checklist.md','PricingView.swift','GalleryView.swift','MainTabView.swift'],
            notes='Product/release planning from docs + UI code.',
        ),
        EvalCase(
            case_id='aitryon_auth_storage_security',
            question='Summarize AiTryOn auth/session persistence and local storage/security boundaries across iOS and Supabase.',
            sources={
                'AuthViewModel.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Auth/AuthViewModel.swift'),
                'AppleSignInService.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Services/AppleSignInService.swift'),
                'KeychainManager.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Core/Utilities/KeychainManager.swift'),
                'LocalDataStore.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Data/LocalStorage/LocalDataStore.swift'),
                'api-contracts.md': read_rel('shared/api-contracts.md'),
            },
            expected_terms=['Apple','Sign','Keychain','session','token','profile','user','models','private','signed','Supabase','auth'],
            expected_sources=['AuthViewModel.swift','AppleSignInService.swift','KeychainManager.swift','LocalDataStore.swift','api-contracts.md'],
            notes='Security/auth/local persistence cross-source question.',
        ),
        EvalCase(
            case_id='aitryon_release_appstore_pipeline',
            question='What is the AiTryOn TestFlight/App Store release pipeline and what files/configs matter for screenshots and metadata?',
            sources={
                'fastlane-README.md': read_rel('ios/AiTryOnNative/fastlane/README.md'),
                'ScreenshotsTests.swift': read_rel('ios/AiTryOnNative/AiTryOnNativeUITests/ScreenshotsTests.swift'),
                'Info.plist': read_rel('ios/AiTryOnNative/AiTryOnNative/Resources/Info.plist'),
                'app-store-page-README.md': read_rel('app-store-page/README.md') if (REPO/'app-store-page/README.md').exists() else '',
            },
            expected_terms=['fastlane','TestFlight','screenshots','metadata','Info.plist','orientation','App Store','snapshot','release','bundle'],
            expected_sources=['fastlane-README.md','ScreenshotsTests.swift','Info.plist','app-store-page-README.md'],
            notes='Release-management real repo question.',
        ),
    ]

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', default='eval_runs_aitryon')
    args=parser.parse_args(argv)
    output=Path(args.output)
    results=[run_case(c, output) for c in make_cases()]
    summary={
        'runs': len(results),
        'winners': {arm: sum(1 for r in results if r['winner']==arm) for arm in ['no_wiki','raw_context','wiki']},
        'strict_winners': {arm: sum(1 for r in results if r['strict_winner']==arm) for arm in ['no_wiki','raw_context','wiki']},
        'cases': [{'case_id': r['case_id'], 'winner': r['winner'], 'strict_winner': r['strict_winner'], 'scores': r['scores'], 'report': r['paths']['report']} for r in results],
    }
    output.mkdir(exist_ok=True)
    (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
