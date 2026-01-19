import DocumentUpload from "./components/DocumentUpload";
import DocumentList from "./components/DocumentList";

function App() {
  return (
    <div style={{ padding: "1rem" }}>
      <h1>Document Management System</h1>
      <DocumentUpload />
      <hr />
      <DocumentList />
    </div>
  );
}

export default App;
