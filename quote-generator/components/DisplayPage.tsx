import type { DisplayDocument } from '../display/runtimePageBuilder';
import type { CSSProperties } from 'react';
import { getSectionDisplayConfig } from '../display/runtimePageBuilder';
import { sectionRegistry } from './display/sections';
import { PdfBrochureDocument } from './display/PdfBrochureDocument';

export default function DisplayPage({
  documentModel,
  workspaceCanvas = false,
}: {
  documentModel: DisplayDocument;
  /** Workspace-only affordances; never enabled by public or PDF routes. */
  workspaceCanvas?: boolean;
}) {
  return (
    <main
      className="display-page-root"
      data-brand={documentModel.tokens.brandKey}
      data-theme={documentModel.theme.id}
      data-view-mode={documentModel.viewMode}
      style={documentModel.colors.page.style as CSSProperties}
    >

      {documentModel.viewMode === 'pdf' ? <PdfBrochureDocument documentModel={documentModel} /> : documentModel.theme.sectionOrder.map((sectionId) => {
          const Section = sectionRegistry[sectionId] as (props: {
            sectionId: typeof sectionId;
            viewModel: (typeof documentModel.page)[typeof sectionId];
            displayConfig: ReturnType<typeof getSectionDisplayConfig>;
            tokens: typeof documentModel.tokens;
            theme: typeof documentModel.theme;
            viewMode: typeof documentModel.viewMode;
            colorScope: (typeof documentModel.colors.sections)[typeof sectionId];
            pageViewModel?: typeof documentModel.page;
            workspaceCanvas?: boolean;
          }) => React.JSX.Element;
          const displayConfig = getSectionDisplayConfig(
            documentModel.theme,
            sectionId,
            documentModel.viewMode
          );

          if (!displayConfig.visibilityByViewMode[documentModel.viewMode]) {
            return null;
          }

          return (
            <div
              key={sectionId}
              className={`display-color-scope display-color-scope--${documentModel.colors.sections[sectionId].id}`}
              style={{
                ...(documentModel.colors.sections[sectionId].style as CSSProperties),
                ...(sectionId === 'nav' ? { position: 'relative', zIndex: 9999 } : {}),
              }}
            >
              <Section
                sectionId={sectionId}
                viewModel={documentModel.page[sectionId]}
                displayConfig={displayConfig}
                tokens={documentModel.tokens}
                theme={documentModel.theme}
                viewMode={documentModel.viewMode}
                colorScope={documentModel.colors.sections[sectionId]}
                pageViewModel={documentModel.page}
                workspaceCanvas={workspaceCanvas}
              />
            </div>
          );
      })}
    </main>
  );
}
