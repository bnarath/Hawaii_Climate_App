#Flask dependencies
from flask import Flask, jsonify, render_template

#Other dependencies
# Python SQL toolkit and Object Relational Mapper
import sqlalchemy
from sqlalchemy import create_engine, func, inspect
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
#data and date manipulation libraries
import numpy as np
import pandas as pd
import datetime as dt

#relative_db_path
relative_db_path = 'Resources/hawaii.sqlite'

def sqlite_create_session(relative_db_path):
    #####This functions create all the background functions for a successful connections to the db
    #####and returns a session class, mapped classes
    #Create an engine to the hawaii.sqlite database
    engine = create_engine(f"sqlite:///{relative_db_path}", echo=False)
    # reflect an existing database into a new model; reflect the tables
    Base = automap_base()
    Base.prepare(engine, reflect=True)

    # Save references to each table
    Measurement = Base.classes.measurement
    Station = Base.classes.station

    # Create our session (link) from Python to the DB
    session = Session(bind=engine)
    return session, Measurement, Station 

def date_prcp_avg_last_n(session, Measurement, Days=366):
    ####This function retrieves the last n Days(by default 366 days) of data from the Measurement class
    ####Returns a dictionary with key as date and value as another dictionary with precipitation: [list] and 
    ####avg precipitation: value

    ### Design a query to retrieve the last 12 months of precipitation data and plot the results
    last_date = session.query(Measurement.date).order_by(Measurement.date.desc()).limit(1).scalar()
    ### Last one year mark in the dataset
    One_year_mark = dt.datetime.strptime(last_date, "%Y-%m-%d")-dt.timedelta(days=Days)
    ### Perform a query to retrieve the data and precipitation scores
    #sql alchemy understands the DateTime dtype and converts that to string implicitly!!
    last_one_year_prcp = session.query(Measurement.date, Measurement.prcp).filter(
        (Measurement.date >= One_year_mark)).order_by(Measurement.date).all()

    ### Save the query results as a Pandas DataFrame and set the index to the date column
    last_one_year_prcp_DF = pd.DataFrame(last_one_year_prcp, columns=['Date','precipitation'])
    #Drop NAs
    last_one_year_prcp_DF.dropna(inplace=True, how='any')
    #Since each day has multiple precipitation data (corresponding to different stations, we can think of providing
    # a list of precipitation values, also, an avg precipitation value)
    #please ensure pandas >= 0.25 to be available to run the below code
    last_one_year_prcp_Agg = last_one_year_prcp_DF.groupby('Date').aggregate(precipitation = ('precipitation', lambda x: x.to_list()),\
                                                avg_precipitation = ('precipitation', lambda x: np.round(np.mean(x), 4)))

    #Convert the DF to a dictionary
    date_prcp_avg_dict = last_one_year_prcp_Agg.T.to_dict()
    return date_prcp_avg_dict    

def get_stations(session,Measurement, Station):
    ####This function returns the Stations
    #return list(np.ravel(session.query(func.distinct(Measurement.station)).all()))
    #Join measurement data with station and get the distinct values of station name (This is the ideal way!!)
    return list(np.ravel(session.query(func.distinct(Station.name))\
.filter(Measurement.station == Station.station).all()))

def get_most_active_station_tobs(session,Measurement, Days=366):
    #Which station has the highest number of observations?
    #create a subquery
    station_observation = session.query(Measurement.station.label("station"), func.count(Measurement.station).label("DataPoints")).\
    group_by(Measurement.station).subquery()

    most_active_station = session.query(station_observation.c.station).order_by(station_observation.c.DataPoints.desc()).limit(1).scalar()
    
    ### Design a query to retrieve the last 12 months of precipitation data and plot the results
    last_date = session.query(Measurement.date).order_by(Measurement.date.desc()).limit(1).scalar()
    ### Last one year mark in the dataset
    One_year_mark = dt.datetime.strptime(last_date, "%Y-%m-%d")-dt.timedelta(days=Days)
    #Query to obtain the dates and temp for last one year for the most active station
    tobs_date_ma = session.query(Measurement.date, Measurement.tobs)\
    .filter((Measurement.station==most_active_station)&\
            (Measurement.date>=One_year_mark)).all()
    #Temp observations for all available dates for the most active station
    Date_TOBS_DF = pd.DataFrame(tobs_date_ma, columns=['Date', "Temp_Observed"])
    Date_TOBS_DF.set_index('Date', inplace=True)
    #Dictionary with most active station name and date tob values
    return {'Most_Active_Station': {most_active_station : Date_TOBS_DF.T.to_dict()}}

def get_the_agg(session, Measurement, start_date, end_date_in_the_data, end_date=None):
    end_date_taken = end_date if end_date is not None else end_date_in_the_data
    #There is a small error in sql alchemy to process >= and <= the same number. Hence, splitting that up
    if start_date == end_date_taken: 
        result = session.query(func.min(Measurement.tobs).label("TMIN"),\
                func.avg(Measurement.tobs).label("TAVG"),\
                func.max(Measurement.tobs).label("TMAX")).\
                    filter(Measurement.date == dt.datetime.strftime(start_date, "%Y-%m-%d")).all()
    else:
        result = session.query(func.min(Measurement.tobs).label("TMIN"),\
                func.avg(Measurement.tobs).label("TAVG"),\
                func.max(Measurement.tobs).label("TMAX")).\
                    filter((Measurement.date <= end_date_taken)&\
                            (Measurement.date >= start_date)).all()
    INDX = f"{dt.datetime.strftime(start_date, '%Y-%m-%d')}{'' if end_date is None else ' to '+dt.datetime.strftime(end_date, '%Y-%m-%d')}"
    return pd.DataFrame(result, columns=['TMIN', 'TAVG', 'TMAX'], index=[INDX]).T.to_dict() 

    
session, Measurement, Station =  sqlite_create_session(relative_db_path)
start_date_in_the_data = dt.datetime.strptime(session.query(Measurement.date).order_by(Measurement.date).limit(1).scalar(), "%Y-%m-%d")
end_date_in_the_data = dt.datetime.strptime(session.query(Measurement.date).order_by(Measurement.date.desc()).limit(1).scalar(), "%Y-%m-%d")

#Create app
app = Flask(__name__)

#Create routes
@app.route('/')
def home_page():
    return render_template('index.html', name='home_page')

@app.route('/api/v1.0/precipitation')
def precipitation():
    print("GET request at /api/v1.0/precipitation")
    try:
        session, Measurement, Station =  sqlite_create_session(relative_db_path)
        date_prcp_avg_dict = date_prcp_avg_last_n(session, Measurement, Days=366)
        ### Close the session
        session.close()
    except:
        ### Close the session
        session.close()
        return "Server is not able to respond. Please try after some time", 404
    return jsonify(date_prcp_avg_dict)

@app.route('/api/v1.0/stations')
def stations():
    print("GET request at /api/v1.0/stations")
    try:
        session, Measurement, Station =  sqlite_create_session(relative_db_path)
        station_list = get_stations(session,Measurement, Station)
        ### Close the session
        session.close()
    except:
        ### Close the session
        session.close()
        return "Server is not able to respond. Please try after some time", 404
    return jsonify(station_list)

@app.route('/api/v1.0/tobs')
def tobs_for_ma():
    print("GET request at /api/v1.0/tobs")
    try:
        session, Measurement, Station =  sqlite_create_session(relative_db_path)
        most_active_station_date_tobs = get_most_active_station_tobs(session,Measurement)
        ### Close the session
        session.close()
    except:
        ### Close the session
        session.close()
        return "Server is not able to respond. Please try after some time", 404
    return jsonify(most_active_station_date_tobs)

@app.route('/api/v1.0/<start>')
def range_data_start(start):
    print(f"GET request at /api/v1.0/{start}")
    try:
        session, Measurement, Station =  sqlite_create_session(relative_db_path)
        start_date_in_the_data = dt.datetime.strptime(session.query(Measurement.date).order_by(Measurement.date).limit(1).scalar(), "%Y-%m-%d")
        end_date_in_the_data = dt.datetime.strptime(session.query(Measurement.date).order_by(Measurement.date.desc()).limit(1).scalar(), "%Y-%m-%d")
        ### Close the session
        session.close()
    except:
        ### Close the session
        session.close()
        return "Server is not able to respond. Please try after some time", 404

    if start is None:
        return "Enter a start date", 404
    else:
        #Parse the data
        try:
            start_date = dt.datetime.strptime(start, "%Y-%m-%d")
        except:
            return "Enter a correct start date in the Year-Month-Day format eg. 2016-08-23", 404
        
        #Date out of range
        if (start_date<start_date_in_the_data):
            return  "We have data between 2010-01-01 and 2017-08-23. Enter start date accordingly", 404
        
        #Retrieve the summary
        try:
            session, Measurement, Station =  sqlite_create_session(relative_db_path)
            agg_result = get_the_agg(session, Measurement, start_date, end_date_in_the_data)
            ### Close the session
            session.close()
            return agg_result

        except:
            ### Close the session
            session.close()
            return "Server is not able to respond. Please try after some time", 404


@app.route('/api/v1.0/<start>/<end>')
def range_data_start_end(start,end):
    print(f"GET request at /api/v1.0/{start}/{end}")
    try:
        session, Measurement, Station =  sqlite_create_session(relative_db_path)
        start_date_in_the_data = dt.datetime.strptime(session.query(Measurement.date).order_by(Measurement.date).limit(1).scalar(), "%Y-%m-%d")
        end_date_in_the_data = dt.datetime.strptime(session.query(Measurement.date).order_by(Measurement.date.desc()).limit(1).scalar(), "%Y-%m-%d")
        ### Close the session
        session.close()
    except:
        ### Close the session
        session.close()
        return "Server is not able to respond. Please try after some time", 404

    if start is None:
        return "Enter a start date", 404
    else:
        #Parse the data
        try:
            start_date = dt.datetime.strptime(start, "%Y-%m-%d")
            end_date = dt.datetime.strptime(end, "%Y-%m-%d")
        except:
            return "Enter correct start date and end date in the Year-Month-Day format eg. 2016-08-23/2017-01/22", 404
        
        #Date out of range
        if (start_date<start_date_in_the_data) or (end_date>end_date_in_the_data) or (start_date>end_date):
            return  "We have data between 2010-01-01 and 2017-08-23. Enter start date accordingly. Also, start date <= end date", 404
        
        #Retrieve the summary
        try:
            session, Measurement, Station =  sqlite_create_session(relative_db_path)
            agg_result = get_the_agg(session, Measurement, start_date, end_date_in_the_data, end_date)
            ### Close the session
            session.close()
            return agg_result

        except:
            ### Close the session
            session.close()
            return "Server is not able to respond. Please try after some time", 404

if __name__== "__main__":
    #app.run(threaded=True, debug=True, port=5000)
    app.run(threaded=True, port=5000)
