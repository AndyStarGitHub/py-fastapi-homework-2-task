from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy import select, func, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import math
from pprint import pprint

from database import get_db
from database.models import MovieModel, CountryModel, GenreModel, ActorModel, LanguageModel
from database.session_sqlite import get_async_session
from schemas import (
    MovieListResponseSchema,
    MovieDetailResponseSchema,
    MovieCreateSchema,
    MovieCreateResponseSchema,
)
from schemas.movies import GenreSchema, LanguageSchema, ActorSchema, MovieUpdateSchema

router = APIRouter()


@router.get("/movies/")
async def get_movie_list(
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=20),
) -> MovieListResponseSchema:

    result = await db.execute(select(func.count(MovieModel.id)))
    total_items = result.scalar()
    if not total_items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No movies found.")

    total_pages = math.ceil(total_items / per_page)
    offset = (page - 1) * per_page

    stmt = (
        select(MovieModel)
        .options(
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
            selectinload(MovieModel.country),
        )
        .order_by(desc(MovieModel.id))
        .offset(offset)
        .limit(per_page)
    )

    result = await db.scalars(stmt)
    movie_objs = result.all()

    if not movie_objs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No movies found.")

    movies = [MovieDetailResponseSchema.from_orm(movie) for movie in movie_objs]

    base_url = "/theater/movies/"
    prev_page = f"{base_url}?page={page - 1}&per_page={per_page}" if page > 1 else None
    next_page = f"{base_url}?page={page + 1}&per_page={per_page}" if page < total_pages else None

    return MovieListResponseSchema(
        movies=movies,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_items
    )


@router.post("/movies/", status_code=status.HTTP_201_CREATED)
async def create_movie(
        movie_data: MovieCreateSchema,
        db: AsyncSession = Depends(get_db)
) -> MovieCreateResponseSchema:
    existing_movie = await db.scalar(
        select(MovieModel)
        .where(MovieModel.name == movie_data.name)
        .where(MovieModel.date == movie_data.date)
    )
    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{movie_data.name}' and release date '{movie_data.date}' already exists.",
        )
    try:
        country = await db.scalar(select(CountryModel).where(CountryModel.code == movie_data.country))
        if not country:
            country = CountryModel(code=movie_data.country)
            db.add(country)
            await db.flush()
        genres = []
        for genre_name in movie_data.genres:
            genre = await db.scalar(select(GenreModel).where(GenreModel.name == genre_name))
            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                await db.flush()
            genres.append(genre)
        actors = []
        for actor_name in movie_data.actors:
            actor = await db.scalar(select(ActorModel).where(ActorModel.name == actor_name))
            if not actor:
                actor = ActorModel(name=actor_name)
                db.add(actor)
                await db.flush()
            actors.append(actor)
        languages = []
        for language_name in movie_data.languages:
            language = await db.scalar(select(LanguageModel).where(LanguageModel.name == language_name))
            if not language:
                language = LanguageModel(name=language_name)
                db.add(language)
                await db.flush()
            languages.append(language)
        movie = MovieModel(
            name=movie_data.name,
            date=movie_data.date,
            score=movie_data.score,
            overview=movie_data.overview,
            status=movie_data.status,
            budget=movie_data.budget,
            revenue=movie_data.revenue,
            country=country,
            genres=genres,
            actors=actors,
            languages=languages,
        )
        db.add(movie)
        await db.commit()

        return MovieCreateResponseSchema(
            id=movie.id,
            name=movie.name,
            date=movie.date,
            score=movie.score,
            overview=movie.overview,
            status=movie.status,
            budget=movie.budget,
            revenue=movie.revenue,
            country=movie.country.code,
            genres=[GenreSchema.from_orm(genre) for genre in movie.genres],
            actors=[ActorSchema.from_orm(actor) for actor in movie.actors],
            languages=[LanguageSchema.from_orm(language) for language in movie.languages],
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The input data is invalid (e.g., missing required fields, invalid values)"
        )


@router.get("/movies/{movie_id}/", response_model=MovieDetailResponseSchema)
async def get_movie_by_id(movie_id: int, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
            selectinload(MovieModel.country),
        )
        .where(MovieModel.id == movie_id)
    )
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    return MovieDetailResponseSchema.from_orm(movie)


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def remove_movie(movie_id: int, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
            selectinload(MovieModel.country),
        )
        .where(MovieModel.id == movie_id)
    )
    deleted_movie = result.scalar_one_or_none()
    if deleted_movie is None:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")

    await session.delete(deleted_movie)
    await session.commit()


@router.patch("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def update_movie(
        movie_id: int,
        movie: MovieUpdateSchema = Body(...),
        session: AsyncSession = Depends(get_async_session),
):
    print("\n==== PATCH /movies request body ====")
    pprint(movie.dict())
    movie_to_update = await get_movie_by_id(movie_id, session)
    if not movie_to_update:
        raise HTTPException(status_code=404, detail="Movie with the given ID was not found.")
    try:
        result = await session.execute(
            select(MovieModel)
            .options(
                selectinload(MovieModel.genres),
                selectinload(MovieModel.actors),
                selectinload(MovieModel.languages),
                selectinload(MovieModel.country),
            )
            .where(MovieModel.id == movie_id)
        )
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")

        update_movie = result.scalar_one_or_none()
        if update_movie is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie with the given ID was not found.")

        if movie.name is not None:
            update_movie.name = movie.name
        if movie.date is not None:
            update_movie.date = movie.date
        if movie.score is not None:
            update_movie.score = movie.score
        if movie.overview is not None:
            update_movie.overview = movie.overview
        if movie.status is not None:
            update_movie.status = movie.status
        if movie.budget is not None:
            update_movie.budget = movie.budget
        if movie.revenue is not None:
            update_movie.revenue = movie.revenue

        if movie.country:
            country_obj = await session.scalar(select(CountryModel).where(CountryModel.code == movie.country))
            if not country_obj:
                raise HTTPException(status_code=400, detail="Invalid country code")
            update_movie.country = country_obj

        if movie.genres is not None:
            result_genres = await session.execute(
                select(GenreModel).where(GenreModel.name.in_(movie.genres))
            )
            db_genres = result_genres.scalars().all()
            update_movie.genres = db_genres

        if movie.actors is not None:
            result_actors = await session.execute(
                select(ActorModel).where(ActorModel.name.in_(movie.actors))
            )
            db_actors = result_actors.scalars().all()
            update_movie.actors = db_actors

        if movie.languages is not None:
            result_languages = await session.execute(
                select(LanguageModel).where(LanguageModel.name.in_(movie.languages))
            )
            db_languages = result_languages.scalars().all()
            update_movie.languages = db_languages

        await session.commit()
        await session.refresh(update_movie)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Something went wrong while updating the movie."
        )

    return {"detail": "Movie updated successfully."}
