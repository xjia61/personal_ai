from pydantic import BaseModel, ConfigDict


class ApplicationProfileUpdate(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""

    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""

    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""

    authorized_to_work: bool = True
    requires_sponsorship: bool = False


class ApplicationProfileOut(ApplicationProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int