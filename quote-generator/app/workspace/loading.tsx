export default function WorkspaceLoading() {
  return (
    <div className="workspace-route-loading" aria-busy="true" aria-label="Loading workspace">
      <div className="workspace-skeleton">
        <div className="workspace-skeleton__line workspace-skeleton__line--wide" />
        <div className="workspace-skeleton__line workspace-skeleton__line--mid" />
        <div className="workspace-skeleton__line" />
      </div>
    </div>
  );
}
