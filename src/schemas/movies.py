from typing import List, Optional
from datetime import date

from pydantic import BaseModel, ConfigDict, Field
from pydantic_extra_types.country import CountryAlpha2

from database import MovieModel


class ActorSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class LanguageSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class GenreSchema(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class BaseMovieSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date: date
    score: float
    name: str
    genres: str
    overview: str
    crew: str
    orig_title: str
    status: str
    orig_lang: str
    budget: float
    revenue: float
    country: str


class MovieListDetailSchema(BaseModel):
    date: date
    score: float
    name: str
    id: int
    overview: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, movie: MovieModel) -> "MovieListDetailSchema":
        return cls(
            id=movie.id,
            name=movie.name,
            date=movie.date,
            score=movie.score,
            overview=movie.overview,
        )


class MovieDetailResponseSchema(BaseModel):
    date: date
    score: float
    name: str
    id: int
    overview: str
    status: str
    budget: float
    revenue: float
    genres: List[GenreSchema]
    actors: List[ActorSchema]
    languages: List[LanguageSchema]
    orig_title: str
    orig_lang: str
    country: dict

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, movie: MovieModel) -> "MovieDetailResponseSchema":
        return cls(
            id=movie.id,
            name=movie.name,
            date=movie.date,
            score=movie.score,
            overview=movie.overview,
            status=movie.status.value,
            budget=float(movie.budget),
            revenue=movie.revenue,
            genres=[GenreSchema.from_orm(genre) for genre in movie.genres],
            actors=[ActorSchema.from_orm(actor) for actor in movie.actors],
            languages=[LanguageSchema.from_orm(language) for language in movie.languages],
            orig_title=movie.name,
            orig_lang=", ".join([lang.name for lang in movie.languages]),
            country={
                "code": movie.country.code,
                "name": movie.country.name,
                "id": movie.country.id,
            } if movie.country else {},
        )


class CountrySchema(BaseModel):
    id: int
    code: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class MovieListResponseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "movies": [
                        {
                            "id": 1,
                            "name": "Creed III",
                            "date": "2023-03-02",
                            "score": 73,
                            "genres": "Drama, Action",
                            "overview": "After dominating the boxing world, Adonis Creed "
                                        "has been thriving in both his career and family life...",
                            "crew": "Michael B. Jordan, Tessa Thompson",
                            "orig_title": "Creed III",
                            "status": "Released",
                            "orig_lang": "English",
                            "budget": 75000000,
                            "revenue": 271616668,
                            "country": "AU"
                        }
                    ],
                    "prev_page": "/theater/movies/?page=1&per_page=10",
                    "next_page": "/theater/movies/?page=3&per_page=10",
                    "total_pages": 1000,
                    "total_items": 9999
                }
            ]
        }
    )
    movies: list[MovieListDetailSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class MovieListItemSchema(BaseMovieSchema):
    id: int


class MovieDetailSchema(BaseMovieSchema):
    id: int


class MovieCreateSchema(BaseModel):
    name: str
    date: date
    score: float = Field(ge=0, le=100)
    overview: str
    status: str
    budget: float = Field(ge=0)
    revenue: float = Field(ge=0)
    country: CountryAlpha2
    genres: List[str]
    actors: List[str]
    languages: List[str]


class MovieCreateResponseSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float
    country: str
    genres: List[GenreSchema]
    actors: List[ActorSchema]
    languages: List[LanguageSchema]
    model_config = ConfigDict(from_attributes=True)


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = None
    date: Optional[date] = None
    score: Optional[float] = Field(default=None, ge=0, le=100)
    overview: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = Field(default=None, ge=0)
    revenue: Optional[float] = Field(default=None, ge=0)
    country: Optional[str] = None
    genres: Optional[List[str]] = None
    actors: Optional[List[str]] = None
    languages: Optional[List[str]] = None
