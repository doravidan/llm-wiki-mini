from __future__ import annotations
import argparse, json
from pathlib import Path
from .harness import EvalCase, run_case

REPO = Path('/Users/doravidan/Projects/style-my-look')


def read_rel(rel: str, limit: int = 32000) -> str:
    path = REPO / rel
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8', errors='ignore')[:limit]


def make_cases() -> list[EvalCase]:
    return [
        EvalCase(
            case_id='holdout_extract_image_url_import',
            question='Explain the URL import/extract-image flow across web or native clients and the Supabase edge function, including request fields, response fields, and failure modes.',
            sources={
                'extract-image-index.ts': read_rel('supabase/functions/extract-image/index.ts'),
                'EdgeFunctionClient.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Data/Networking/EdgeFunctionClient.swift'),
                'StudioViewModel.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Studio/StudioViewModel.swift'),
                'Studio.tsx': read_rel('src/pages/Studio.tsx'),
                'api-contracts.md': read_rel('shared/api-contracts.md'),
            },
            expected_terms=['extract-image','url','imageUrl','image_url','source','alternatives','failure','edge','function','garment'],
            expected_sources=['extract-image-index.ts','EdgeFunctionClient.swift','StudioViewModel.swift','Studio.tsx','api-contracts.md'],
            notes='Held-out URL import flow not used in initial AiTryOn eval.',
        ),
        EvalCase(
            case_id='holdout_paypal_web_ios_gap',
            question='How does PayPal purchasing work today, and what is the web/iOS gap for credit packs and subscriptions?',
            sources={
                'paypal-index.ts': read_rel('supabase/functions/paypal/index.ts'),
                'Pricing.tsx': read_rel('src/pages/Pricing.tsx'),
                'PricingView.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Pricing/PricingView.swift'),
                'feature-parity-checklist.md': read_rel('shared/feature-parity-checklist.md'),
                'api-contracts.md': read_rel('shared/api-contracts.md'),
            },
            expected_terms=['PayPal','create-order','capture-order','subscription','credit','pack','web','iOS','SDK','payment'],
            expected_sources=['paypal-index.ts','Pricing.tsx','PricingView.swift','feature-parity-checklist.md','api-contracts.md'],
            notes='Held-out monetization cross-platform gap.',
        ),
        EvalCase(
            case_id='holdout_generation_profitability_metadata',
            question='What generation profitability metadata is tracked and how does it relate to feature credit costs in generate-tryon?',
            sources={
                'generation-profitability.sql': read_rel('supabase/migrations/20260429123000_generation_profitability_metadata.sql'),
                'generate-tryon-index.ts': read_rel('supabase/functions/generate-tryon/index.ts'),
                'Generation.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Data/Models/Generation.swift'),
                'api-contracts.md': read_rel('shared/api-contracts.md'),
            },
            expected_terms=['profitability','metadata','feature','credit','cost','provider','estimated','generation','variation','capsule'],
            expected_sources=['generation-profitability.sql','generate-tryon-index.ts','Generation.swift','api-contracts.md'],
            notes='Held-out business/infra metadata case.',
        ),
        EvalCase(
            case_id='holdout_storage_rls_boundaries',
            question='Summarize storage bucket access and RLS/security boundaries for models, generations, and closet items.',
            sources={
                'storage_policies.sql': read_rel('supabase/storage_policies.sql'),
                'create_closet_items.sql': read_rel('supabase/migrations/20260104000000_create_closet_items.sql'),
                'LocalDataStore.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Data/LocalStorage/LocalDataStore.swift'),
                'api-contracts.md': read_rel('shared/api-contracts.md'),
            },
            expected_terms=['storage','bucket','models','generations','closet','RLS','policy','private','public','user_id'],
            expected_sources=['storage_policies.sql','create_closet_items.sql','LocalDataStore.swift','api-contracts.md'],
            notes='Held-out storage/security boundary case.',
        ),
        EvalCase(
            case_id='holdout_gallery_delete_remix_flow',
            question='How do gallery delete, share/download, fullscreen viewing, and remix flows differ or connect between web and iOS?',
            sources={
                'GalleryView.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Gallery/GalleryView.swift'),
                'GalleryViewModel.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Gallery/GalleryViewModel.swift'),
                'Gallery.tsx': read_rel('src/pages/Gallery.tsx'),
                'feature-parity-checklist.md': read_rel('shared/feature-parity-checklist.md'),
            },
            expected_terms=['gallery','delete','share','download','fullscreen','remix','web','iOS','swipe','keyboard'],
            expected_sources=['GalleryView.swift','GalleryViewModel.swift','Gallery.tsx','feature-parity-checklist.md'],
            notes='Held-out gallery UX and parity case.',
        ),
        EvalCase(
            case_id='holdout_design_system_native_web',
            question='What design system/style tokens and premium visual patterns are used across native iOS and web?',
            sources={
                'DesignSystem.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Theme/DesignSystem.swift'),
                'AppTheme.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Theme/AppTheme.swift'),
                'StyleGuide.tsx': read_rel('src/pages/StyleGuide.tsx'),
                'Landing.tsx': read_rel('src/pages/Landing.tsx'),
            },
            expected_terms=['design','theme','color','gradient','glass','premium','dark','typography','spacing','animation'],
            expected_sources=['DesignSystem.swift','AppTheme.swift','StyleGuide.tsx','Landing.tsx'],
            notes='Held-out design/style product case.',
        ),
        EvalCase(
            case_id='holdout_onboarding_profile_measurements',
            question='How does onboarding collect or store profile information and body measurements, and which models/migrations support it?',
            sources={
                'OnboardingView.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Onboarding/OnboardingView.swift'),
                'OnboardingViewModel.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Onboarding/OnboardingViewModel.swift'),
                'Profile.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Data/Models/Profile.swift'),
                'add_profile_measurements.sql': read_rel('supabase/migrations/20260111000000_add_profile_measurements.sql'),
                'add_profile_photo_gender.sql': read_rel('supabase/migrations/20260111210000_add_profile_photo_gender.sql'),
            },
            expected_terms=['onboarding','profile','measurements','height','weight','gender','photo','body','Supabase','migration'],
            expected_sources=['OnboardingView.swift','OnboardingViewModel.swift','Profile.swift','add_profile_measurements.sql','add_profile_photo_gender.sql'],
            notes='Held-out user profile/onboarding data case.',
        ),
        EvalCase(
            case_id='holdout_apple_auth_native_vs_edge',
            question='What is the relationship between native Apple Sign-In, the apple-auth edge function, Supabase provider setup, and profile apple_id fields?',
            sources={
                'AppleSignInService.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Services/AppleSignInService.swift'),
                'apple-auth-index.ts': read_rel('supabase/functions/apple-auth/index.ts'),
                'add_apple_id_to_profiles.sql': read_rel('supabase/migrations/20260112130000_add_apple_id_to_profiles.sql'),
                'SUPABASE_MIGRATION_GUIDE.md': read_rel('SUPABASE_MIGRATION_GUIDE.md'),
                'AuthViewModel.swift': read_rel('ios/AiTryOnNative/AiTryOnNative/Presentation/Screens/Auth/AuthViewModel.swift'),
            },
            expected_terms=['Apple','Sign-In','native','apple-auth','edge','provider','apple_id','profile','Supabase','com.aitry.on'],
            expected_sources=['AppleSignInService.swift','apple-auth-index.ts','add_apple_id_to_profiles.sql','SUPABASE_MIGRATION_GUIDE.md','AuthViewModel.swift'],
            notes='Held-out auth architecture/versioning case.',
        ),
    ]


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', default='eval_runs_aitryon_holdout')
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
