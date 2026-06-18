import { isHtmlCommunicationBody } from "./utils";

type ResearchCommunicationBodyPreviewProps = {
  body: string;
  id?: string;
};

export default function ResearchCommunicationBodyPreview({
  body,
  id,
}: ResearchCommunicationBodyPreviewProps) {
  if (isHtmlCommunicationBody(body)) {
    return (
      <div className="research-communication-html-preview" id={id}>
        <iframe title="Email preview" sandbox="" srcDoc={body} />
      </div>
    );
  }

  return (
    <pre className="draft-research-communication-body" id={id}>
      {body}
    </pre>
  );
}
