import { useNavigate } from "react-router-dom";
import { createProject } from "../api/projects";
import ProjectForm from "../components/ProjectForm";
import { notifySuccess } from "../lib/toast";

export default function CreateProject() {
  const navigate = useNavigate();

  async function handleSubmit(formData) {
    try {
      const response = await createProject(formData);

      notifySuccess("Project published successfully.");
      navigate("/projects/" + response.data.id);
    } catch (error) {
      console.error(error);
    }
  }

  return (
    <div>
      <div className="container" style={{ paddingTop: 40 }}>
        <h1 className="section-heading">Create a New Campaign</h1>

        <p style={{ color: "var(--ink-600)", marginTop: -14 }}>
          Add the details of your project and share your idea with the community.
        </p>
      </div>

      <ProjectForm
        onSubmit={handleSubmit}
        submitLabel="Publish Project"
      />
    </div>
  );
}
