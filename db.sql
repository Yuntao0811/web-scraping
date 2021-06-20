create schema condo collate utf8mb4_0900_ai_ci;
use condo;

create table rentals
(
    Name          varchar(30)  not null
        primary key,
    District      varchar(50)  null,
    LeasedPrice   float        null,
    IsLeased      tinyint(1)   null,
    LeaseDt       date         null,
    ListedDay     int          null,
    Size          varchar(20)  null,
    Exposure      varchar(10)  null,
    Furnished     varchar(10)  null,
    Possession    varchar(20)  null,
    AgeOfBuilding varchar(25)  null,
    OuterSpace    varchar(20)  null,
    HasHydro      varchar(10)  null,
    Locker        varchar(20)  null,
    Heating       varchar(20)  null,
    ParkingType   varchar(20)  null,
    PropertyType  varchar(30)  null,
    Haslaundry    varchar(10)  null,
    HasWater      varchar(10)  null,
    Parking       varchar(10)  null,
    CorpNo        varchar(30)  null,
    Url           varchar(250) null
);
